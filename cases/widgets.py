from django.forms.widgets import Widget
from django.forms.fields import Field
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.template.loader import render_to_string
from nes.core.identifiers.validators import validate_entity_id
import json
from json import JSONDecodeError


class BaseMultiWidget(Widget):
    template_name = None

    class Media:
        css = {
            "all": (
                "cases/css/widgets.css",
                "https://nepalidatepicker.sajanmaharjan.com.np/v5/nepali.datepicker/css/nepali.datepicker.v5.0.6.min.css",
            )
        }
        js = (
            "cases/js/widgets.js",
            "https://nepalidatepicker.sajanmaharjan.com.np/v5/nepali.datepicker/js/nepali.datepicker.v5.0.6.min.js",
            "cases/js/date_converter.js",
        )

    def get_context(self, name, value, attrs):
        if value is None:
            value = []
        elif isinstance(value, str):
            value = json.loads(value) if value else []

        final_attrs = self.build_attrs(self.attrs, attrs)
        widget_id = final_attrs.get("id", name)

        return {
            "widget_id": widget_id,
            "name": name,
            "values": value,
            "values_json": json.dumps(value),
        }

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        value = data.get(name, "[]")
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []


class MultiEntityIDWidget(BaseMultiWidget):
    template_name = "cases/widgets/multi_entity_widget.html"


class MultiEntityIDField(Field):
    widget = MultiEntityIDWidget

    def to_python(self, value):
        if value in self.empty_values:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    def validate(self, value):
        super().validate(value)
        for entity_id in value:
            try:
                validate_entity_id(entity_id)
            except ValueError as e:
                raise ValidationError(str(e))


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
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

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
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []


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
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []


class MultiURLWidget(BaseMultiWidget):
    template_name = "cases/widgets/multi_url_widget.html"

    def __init__(self, attrs=None, button_label=None):
        super().__init__(attrs)
        self.button_label = button_label or "Add URL"

    def get_context(self, name, value, attrs):
        """
        Override to handle invalid JSON gracefully.
        If JSON parsing fails, treat as empty list so form can render with validation error.
        """
        if value is None:
            value = []
        elif isinstance(value, str):
            try:
                value = json.loads(value) if value else []
            except (JSONDecodeError, TypeError):
                # Invalid JSON - use empty list so form can render and show validation error
                value = []

        final_attrs = self.build_attrs(self.attrs, attrs)
        widget_id = final_attrs.get("id", name)

        context = {
            "widget_id": widget_id,
            "name": name,
            "values": value,
            "values_json": json.dumps(value),
            "button_label": self.button_label,
        }
        return context

    def value_from_datadict(self, data, files, name):
        """
        Extract value from form data without silently converting parse errors to [].
        Let MultiURLField.to_python() handle JSON parsing and raise ValidationError.
        """
        value = data.get(name, "[]")
        return value if value is not None else "[]"


class MultiURLField(Field):
    def __init__(self, *args, button_label="Add URL", **kwargs):
        self.button_label = button_label
        super().__init__(*args, **kwargs)
        self.widget = MultiURLWidget(button_label=button_label)

    def to_python(self, value):
        if value in self.empty_values:
            return []
        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(value) if value else []
        except (JSONDecodeError, TypeError) as err:
            raise ValidationError("Invalid URL payload format.") from err

        if not isinstance(parsed, list):
            raise ValidationError("Expected a list of URLs.")
        return parsed

    def validate(self, value):
        super().validate(value)
        # Validate each URL
        if value:
            validator = URLValidator()
            for url in value:
                # Check type before calling .strip()
                if not isinstance(url, str):
                    raise ValidationError(
                        f"Invalid URL type: expected string, got {type(url).__name__} ({url!r})"
                    )

                # Normalize and check if empty
                normalized = url.strip()
                if not normalized:
                    # Reject whitespace-only or empty URLs at form validation time
                    raise ValidationError(
                        f"URL cannot be blank or whitespace-only: {url!r}"
                    )

                try:
                    validator(normalized)
                except ValidationError as err:
                    raise ValidationError(f"Invalid URL: {url}") from err
