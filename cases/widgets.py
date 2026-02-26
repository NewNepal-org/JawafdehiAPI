import json

from django.core.exceptions import ValidationError
from django.forms.fields import Field
from django.forms.widgets import Widget
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from nes.core.identifiers.validators import validate_entity_id


def _parse_json_list(value):
    """
    Parse a value into a list, handling JSON strings and ensuring list output.

    Args:
        value: Raw value (list, string, or None)

    Returns:
        list: Parsed list, or empty list on error
    """
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


class BaseMultiWidget(Widget):
    template_name = None

    class Media:
        css = {"all": ("cases/css/widgets.css",)}  # noqa: RUF012
        js = ("cases/js/widgets.js",)

    def get_context(self, name, value, attrs):
        value = _parse_json_list(value)

        final_attrs = self.build_attrs(self.attrs, attrs)
        widget_id = final_attrs.get("id", name)

        return {
            "widget_id": widget_id,
            "name": name,
            "values": value,
            "values_json": json.dumps(value),
        }

    def render(self, name, value, attrs=None, renderer=None):  # noqa: ARG002
        context = self.get_context(name, value, attrs)
        return mark_safe(render_to_string(self.template_name, context))  # noqa: S308

    def value_from_datadict(self, data, files, name):  # noqa: ARG002
        value = data.get(name, "[]")
        return _parse_json_list(value)


class MultiEntityIDWidget(BaseMultiWidget):
    template_name = "cases/widgets/multi_entity_widget.html"


class MultiEntityIDField(Field):
    widget = MultiEntityIDWidget

    def to_python(self, value):
        if value in self.empty_values:
            return []
        return _parse_json_list(value)

    def validate(self, value):
        super().validate(value)
        for entity_id in value:
            try:
                validate_entity_id(entity_id)
            except ValueError as e:
                raise ValidationError(str(e)) from e


class MultiTextWidget(BaseMultiWidget):
    template_name = "cases/widgets/multi_text_widget.html"

    def __init__(self, attrs=None, button_label=None):
        super().__init__(attrs)
        self.button_label = button_label or "Add Item"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["button_label"] = self.button_label
        return context


class MultiTextField(Field):
    def __init__(self, *args, button_label="Add Item", **kwargs):
        self.button_label = button_label
        super().__init__(*args, **kwargs)
        self.widget = MultiTextWidget(button_label=button_label)

    def to_python(self, value):
        if value in self.empty_values:
            return []
        return _parse_json_list(value)

    def validate(self, value):
        super().validate(value)
        # Only validate non-empty if field is required
        if self.required and (not value or len(value) < 1):
            raise ValidationError("This field is required.")


class MultiTimelineWidget(BaseMultiWidget):
    template_name = "cases/widgets/multi_timeline_widget.html"


class MultiTimelineField(Field):
    widget = MultiTimelineWidget

    def to_python(self, value):
        if value in self.empty_values:
            return []
        return _parse_json_list(value)


class MultiEvidenceWidget(BaseMultiWidget):
    template_name = "cases/widgets/multi_evidence_widget.html"

    def __init__(self, attrs=None, sources=None):
        super().__init__(attrs)
        self.sources = sources or []

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["sources"] = self.sources
        return context


class MultiEvidenceField(Field):
    def __init__(self, *args, **kwargs):
        self.sources = kwargs.pop("sources", [])
        super().__init__(*args, **kwargs)
        self.widget = MultiEvidenceWidget(sources=self.sources)

    def to_python(self, value):
        if value in self.empty_values:
            return []
        return _parse_json_list(value)
