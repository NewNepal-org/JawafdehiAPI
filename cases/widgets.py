from django import forms
from django.forms.widgets import Widget
from django.forms.fields import Field
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from nes.core.identifiers.validators import validate_entity_id
import json


class BaseMultiWidget(Widget):
    input_class = 'multi-input'
    button_label = 'Add Item'
    
    def get_row_html(self, value, widget_id):
        raise NotImplementedError
    
    def get_row_template(self):
        raise NotImplementedError
    
    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = []
        elif isinstance(value, str):
            value = json.loads(value) if value else []
        
        final_attrs = self.build_attrs(self.attrs, attrs)
        widget_id = final_attrs.get('id', name)
        
        html = f'<div id="{widget_id}_container" class="multiple-input-container">'
        
        for val in value:
            html += self.get_row_html(val, widget_id)
        
        html += f'<div style="margin-bottom: 8px;">'
        html += f'<button type="button" id="{widget_id}_add" class="btn btn-sm btn-success" style="padding: 2px 8px;"><i class="fas fa-plus"></i> {self.button_label}</button>'
        html += '</div></div>'
        html += f'<input type="hidden" name="{name}" id="{widget_id}" value=\'{json.dumps(value)}\'>'
        
        html += f'''
        <script>
        (function() {{
            const container = document.getElementById('{widget_id}_container');
            const hiddenInput = document.getElementById('{widget_id}');
            const addBtn = document.getElementById('{widget_id}_add');
            
            function updateHidden() {{
                const inputs = container.querySelectorAll('.{self.input_class}');
                const values = {self.get_update_logic()};
                hiddenInput.value = JSON.stringify(values);
            }}
            
            addBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                const row = document.createElement('div');
                row.className = 'input-row';
                row.innerHTML = '{self.get_row_template()}';
                {self.get_row_styles()}
                addBtn.parentElement.insertAdjacentElement('beforebegin', row);
                row.querySelectorAll('.{self.input_class}').forEach(inp => inp.addEventListener('input', updateHidden));
                row.querySelector('.remove-input').addEventListener('click', function() {{
                    row.remove();
                    updateHidden();
                }});
            }});
            
            container.addEventListener('click', function(e) {{
                if (e.target.classList.contains('remove-input')) {{
                    e.preventDefault();
                    e.target.parentElement.remove();
                    updateHidden();
                }}
            }});
            
            container.addEventListener('input', function(e) {{
                if (e.target.classList.contains('{self.input_class}')) {{
                    updateHidden();
                }}
            }});
            
            let draggedRow = null;
            container.addEventListener('dragstart', function(e) {{
                if (e.target.classList.contains('input-row')) {{
                    draggedRow = e.target;
                    e.target.style.opacity = '0.5';
                }}
            }});
            
            container.addEventListener('dragend', function(e) {{
                if (e.target.classList.contains('input-row')) {{
                    e.target.style.opacity = '1';
                }}
            }});
            
            container.addEventListener('dragover', function(e) {{
                e.preventDefault();
                const afterElement = getDragAfterElement(container, e.clientY);
                if (afterElement == null) {{
                    const rows = container.querySelectorAll('.input-row');
                    if (rows.length > 0) container.insertBefore(draggedRow, addBtn.parentElement);
                }} else {{
                    container.insertBefore(draggedRow, afterElement);
                }}
            }});
            
            container.addEventListener('drop', function(e) {{
                e.preventDefault();
                updateHidden();
            }});
            
            function getDragAfterElement(container, y) {{
                const draggableElements = [...container.querySelectorAll('.input-row:not(.dragging)')];
                return draggableElements.reduce((closest, child) => {{
                    const box = child.getBoundingClientRect();
                    const offset = y - box.top - box.height / 2;
                    if (offset < 0 && offset > closest.offset) {{
                        return {{ offset: offset, element: child }};
                    }} else {{
                        return closest;
                    }}
                }}, {{ offset: Number.NEGATIVE_INFINITY }}).element;
            }}
        }})();
        </script>
        '''
        
        return mark_safe(html)
    
    def get_update_logic(self):
        return f"Array.from(inputs).map(i => i.value.trim()).filter(v => v)"
    
    def get_row_styles(self):
        return "row.style.marginBottom = '8px'; row.style.display = 'flex'; row.style.alignItems = 'center'; row.draggable = true; row.style.cursor = 'move';"
    
    def value_from_datadict(self, data, files, name):
        value = data.get(name, '[]')
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except:
            return []


class MultiEntityIDWidget(BaseMultiWidget):
    input_class = 'entity-input'
    button_label = 'Add Entity'
    
    def get_row_html(self, value, widget_id):
        return f'<div class="input-row" draggable="true" style="margin-bottom: 8px; display: flex; align-items: center;"><span class="drag-handle" style="cursor: move; padding: 4px 8px; margin-right: 4px;">⋮⋮</span><input type="text" value="{value}" style="width: 300px; margin-right: 8px;" class="entity-input"><button type="button" class="btn btn-sm btn-danger remove-input" style="padding: 2px 8px;"><i class="fas fa-times"></i></button></div>'
    
    def get_row_template(self):
        return '<span class="drag-handle" style="cursor: move; padding: 4px 8px; margin-right: 4px;">⋮⋮</span><input type="text" style="width: 300px; margin-right: 8px;" class="entity-input"> <button type="button" class="btn btn-sm btn-danger remove-input" style="padding: 2px 8px;"><i class="fas fa-times"></i></button>'


class MultiEntityIDField(Field):
    widget = MultiEntityIDWidget
    
    def to_python(self, value):
        if value in self.empty_values:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except:
            return []
    
    def validate(self, value):
        super().validate(value)
        for entity_id in value:
            try:
                validate_entity_id(entity_id)
            except ValueError as e:
                raise ValidationError(str(e))
    
    def prepare_value(self, value):
        if isinstance(value, list):
            return value
        return value


class MultiTextWidget(BaseMultiWidget):
    input_class = 'text-input'
    button_label = 'Add Item'
    
    def __init__(self, attrs=None, button_label=None):
        super().__init__(attrs)
        if button_label:
            self.button_label = button_label
    
    def get_row_html(self, value, widget_id):
        return f'<div class="input-row" draggable="true" style="margin-bottom: 8px; display: flex; align-items: center;"><span class="drag-handle" style="cursor: move; padding: 4px 8px; margin-right: 4px;">⋮⋮</span><input type="text" value="{value}" style="width: 500px; margin-right: 8px;" class="text-input"><button type="button" class="btn btn-sm btn-danger remove-input" style="padding: 2px 8px;"><i class="fas fa-times"></i></button></div>'
    
    def get_row_template(self):
        return '<span class="drag-handle" style="cursor: move; padding: 4px 8px; margin-right: 4px;">⋮⋮</span><input type="text" style="width: 500px; margin-right: 8px;" class="text-input"> <button type="button" class="btn btn-sm btn-danger remove-input" style="padding: 2px 8px;"><i class="fas fa-times"></i></button>'


class MultiTextField(Field):
    def __init__(self, *args, button_label='Add Item', **kwargs):
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
        except:
            return []
    
    def validate(self, value):
        super().validate(value)
        # Only validate non-empty if field is required
        if self.required and (not value or len(value) < 1):
            raise ValidationError("This field is required.")
    
    def prepare_value(self, value):
        if isinstance(value, list):
            return value
        return value


class MultiTimelineWidget(BaseMultiWidget):
    input_class = 'timeline-input'
    button_label = 'Add Timeline Entry'
    
    def get_row_html(self, value, widget_id):
        from django.utils.html import escape
        # Support both 'date' and 'event_date' keys for backwards compatibility
        date_val = (value.get('date') or value.get('event_date', '')).strip() if isinstance(value, dict) else ''
        title_val = escape(value.get('title', '')) if isinstance(value, dict) else ''
        desc_val = escape(value.get('description', '')) if isinstance(value, dict) else ''
        return f'<div class="input-row" draggable="true" style="margin-bottom: 16px; padding: 12px; border: 1px solid #ddd; border-radius: 4px; position: relative;"><span class="drag-handle" style="cursor: move; padding: 4px 8px; position: absolute; left: 8px; top: 8px;">⋮⋮</span><button type="button" class="btn btn-sm btn-danger remove-input" style="position: absolute; top: 8px; right: 8px; padding: 2px 8px;"><i class="fas fa-times"></i></button><div style="margin-bottom: 8px; margin-left: 32px;"><label style="display: block; margin-bottom: 4px; font-weight: 500;">Date</label><input type="date" value="{date_val}" style="width: 200px;" class="timeline-input" placeholder="Date"></div><div style="margin-bottom: 8px; margin-left: 32px;"><label style="display: block; margin-bottom: 4px; font-weight: 500;">Title</label><textarea style="width: calc(100% - 32px); min-height: 40px; resize: vertical;" class="timeline-input" placeholder="Title">{title_val}</textarea></div><div style="margin-left: 32px;"><label style="display: block; margin-bottom: 4px; font-weight: 500;">Description (optional)</label><textarea style="width: calc(100% - 32px); min-height: 60px; resize: vertical;" class="timeline-input" placeholder="Description">{desc_val}</textarea></div></div>'
    
    def get_row_template(self):
        return '<span class="drag-handle" style="cursor: move; padding: 4px 8px; position: absolute; left: 8px; top: 8px;">⋮⋮</span><button type="button" class="btn btn-sm btn-danger remove-input" style="position: absolute; top: 8px; right: 8px; padding: 2px 8px;"><i class="fas fa-times"></i></button><div style="margin-bottom: 8px; margin-left: 32px;"><label style="display: block; margin-bottom: 4px; font-weight: 500;">Date</label><input type="date" style="width: 200px;" class="timeline-input" placeholder="Date"></div><div style="margin-bottom: 8px; margin-left: 32px;"><label style="display: block; margin-bottom: 4px; font-weight: 500;">Title</label><textarea style="width: calc(100% - 32px); min-height: 40px; resize: vertical;" class="timeline-input" placeholder="Title"></textarea></div><div style="margin-left: 32px;"><label style="display: block; margin-bottom: 4px; font-weight: 500;">Description (optional)</label><textarea style="width: calc(100% - 32px); min-height: 60px; resize: vertical;" class="timeline-input" placeholder="Description"></textarea></div>'
    
    def get_update_logic(self):
        return "Array.from(container.querySelectorAll('.input-row')).map(row => { const inputs = row.querySelectorAll('.timeline-input'); return inputs[0].value || inputs[1].value || inputs[2].value ? {date: inputs[0].value.trim(), title: inputs[1].value.trim(), description: inputs[2].value.trim()} : null; }).filter(v => v)"
    
    def get_row_styles(self):
        return "row.style.marginBottom = '16px'; row.style.padding = '12px'; row.style.border = '1px solid #ddd'; row.style.borderRadius = '4px'; row.style.position = 'relative'; row.draggable = true;"


class MultiTimelineField(Field):
    widget = MultiTimelineWidget
    
    def to_python(self, value):
        if value in self.empty_values:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except:
            return []
    
    def prepare_value(self, value):
        if isinstance(value, list):
            # Normalize event_date to date for backwards compatibility
            normalized = []
            for item in value:
                if isinstance(item, dict):
                    normalized_item = item.copy()
                    # If event_date exists but date doesn't, rename it
                    if 'event_date' in normalized_item and 'date' not in normalized_item:
                        normalized_item['date'] = normalized_item.pop('event_date')
                    normalized.append(normalized_item)
                else:
                    normalized.append(item)
            return normalized
        return value


class MultiEvidenceWidget(BaseMultiWidget):
    input_class = 'evidence-input'
    button_label = 'Add Evidence'
    
    def __init__(self, attrs=None, sources=None):
        super().__init__(attrs)
        self.sources = sources or []
    
    def get_row_html(self, value, widget_id):
        source_id = value.get('source_id', '') if isinstance(value, dict) else ''
        desc_val = value.get('description', '') if isinstance(value, dict) else ''
        options = ''.join([f'<option value="{s[0]}" {"selected" if s[0] == source_id else ""}>{s[1]}</option>' for s in self.sources])
        return f'<div class="input-row" draggable="true" style="margin-bottom: 16px; padding: 12px; border: 1px solid #ddd; border-radius: 4px; position: relative;"><span class="drag-handle" style="cursor: move; padding: 4px 8px; position: absolute; left: 8px; top: 8px;">⋮⋮</span><button type="button" class="btn btn-sm btn-danger remove-input" style="position: absolute; top: 8px; right: 8px; padding: 2px 8px;"><i class="fas fa-times"></i></button><div style="margin-bottom: 8px; margin-left: 32px;"><label style="display: block; margin-bottom: 4px; font-weight: 500;">Document Source</label><select style="width: 100%;" class="evidence-input">{options}</select><div style="margin-top: 4px;"><a href="/admin/cases/documentsource/add/" target="_blank" style="font-size: 12px;">+ Create new document source</a></div></div><div style="margin-left: 32px;"><label style="display: block; margin-bottom: 4px; font-weight: 500;">Description</label><textarea style="width: calc(100% - 32px); min-height: 60px; resize: vertical;" class="evidence-input" placeholder="Description">{desc_val}</textarea></div></div>'
    
    def get_row_template(self):
        options = ''.join([f'<option value="{s[0]}">{s[1]}</option>' for s in self.sources])
        return f'<span class="drag-handle" style="cursor: move; padding: 4px 8px; position: absolute; left: 8px; top: 8px;">⋮⋮</span><button type="button" class="btn btn-sm btn-danger remove-input" style="position: absolute; top: 8px; right: 8px; padding: 2px 8px;"><i class="fas fa-times"></i></button><div style="margin-bottom: 8px; margin-left: 32px;"><label style="display: block; margin-bottom: 4px; font-weight: 500;">Document Source</label><select style="width: 100%;" class="evidence-input">{options}</select><div style="margin-top: 4px;"><a href="/admin/cases/documentsource/add/" target="_blank" style="font-size: 12px;">+ Create new document source</a></div></div><div style="margin-left: 32px;"><label style="display: block; margin-bottom: 4px; font-weight: 500;">Description</label><textarea style="width: calc(100% - 32px); min-height: 60px; resize: vertical;" class="evidence-input" placeholder="Description"></textarea></div>'
    
    def get_update_logic(self):
        return "Array.from(container.querySelectorAll('.input-row')).map(row => { const inputs = row.querySelectorAll('.evidence-input'); return inputs[0].value || inputs[1].value ? {source_id: inputs[0].value, description: inputs[1].value.trim()} : null; }).filter(v => v)"
    
    def get_row_styles(self):
        return "row.style.marginBottom = '16px'; row.style.padding = '12px'; row.style.border = '1px solid #ddd'; row.style.borderRadius = '4px'; row.style.position = 'relative'; row.draggable = true;"


class MultiEvidenceField(Field):
    def __init__(self, *args, **kwargs):
        self.sources = kwargs.pop('sources', [])
        super().__init__(*args, **kwargs)
        self.widget = MultiEvidenceWidget(sources=self.sources)
    
    def to_python(self, value):
        if value in self.empty_values:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except:
            return []
    
    def prepare_value(self, value):
        if isinstance(value, list):
            return value
        return value
