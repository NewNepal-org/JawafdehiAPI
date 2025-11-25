from django import forms
from django.forms.widgets import Widget
from django.forms.fields import Field
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from nes.core.identifiers.validators import validate_entity_id
import json


class MultiEntityIDWidget(Widget):
    template_name = 'admin/multiple_input_widget.html'
    
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs = attrs or {}
    
    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = []
        elif isinstance(value, str):
            value = json.loads(value) if value else []
        
        final_attrs = self.build_attrs(self.attrs, attrs)
        widget_id = final_attrs.get('id', name)
        
        html = f'<div id="{widget_id}_container" class="multiple-input-container">'
        
        for i, val in enumerate(value):
            html += f'<div class="input-row" style="margin-bottom: 8px; display: flex; align-items: center;">'
            html += f'<input type="text" value="{val}" style="width: 300px; margin-right: 8px;" class="entity-input">'
            html += f'<button type="button" class="btn btn-sm btn-danger remove-input" style="padding: 2px 8px;"><i class="fas fa-times"></i></button>'
            html += '</div>'
        
        html += f'<div style="margin-bottom: 8px;">'
        html += f'<button type="button" id="{widget_id}_add" class="btn btn-sm btn-success" style="padding: 2px 8px;"><i class="fas fa-plus"></i> Add Entity</button>'
        html += '</div>'
        html += '</div>'
        html += f'<input type="hidden" name="{name}" id="{widget_id}" value=\'{json.dumps(value)}\'>'
        
        html += f'''
        <script>
        (function() {{
            const container = document.getElementById('{widget_id}_container');
            const hiddenInput = document.getElementById('{widget_id}');
            const addBtn = document.getElementById('{widget_id}_add');
            
            function updateHidden() {{
                const inputs = container.querySelectorAll('.entity-input');
                const values = Array.from(inputs).map(i => i.value.trim()).filter(v => v);
                hiddenInput.value = JSON.stringify(values);
            }}
            
            addBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                const row = document.createElement('div');
                row.className = 'input-row';
                row.style.marginBottom = '8px';
                row.innerHTML = '<input type="text" style="width: 300px; margin-right: 8px;" class="entity-input"> <button type="button" class="btn btn-sm btn-danger remove-input" style="padding: 2px 8px;"><i class="fas fa-times"></i></button>';
                row.style.display = 'flex';
                row.style.alignItems = 'center';
                container.appendChild(row);
                
                row.querySelector('.remove-input').addEventListener('click', function() {{
                    row.remove();
                    updateHidden();
                }});
                
                row.querySelector('.entity-input').addEventListener('input', updateHidden);
            }});
            
            container.addEventListener('click', function(e) {{
                if (e.target.classList.contains('remove-input')) {{
                    e.preventDefault();
                    e.target.parentElement.remove();
                    updateHidden();
                }}
            }});
            
            container.addEventListener('input', function(e) {{
                if (e.target.classList.contains('entity-input')) {{
                    updateHidden();
                }}
            }});
        }})();
        </script>
        '''
        
        return mark_safe(html)
    
    def value_from_datadict(self, data, files, name):
        value = data.get(name, '[]')
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except:
            return []


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
            validate_entity_id(entity_id)
    
    def prepare_value(self, value):
        if isinstance(value, list):
            return value
        return value


class MultiTextWidget(Widget):
    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = []
        elif isinstance(value, str):
            value = json.loads(value) if value else []
        
        final_attrs = self.build_attrs(self.attrs, attrs)
        widget_id = final_attrs.get('id', name)
        
        html = f'<div id="{widget_id}_container" class="multiple-input-container">'
        
        for i, val in enumerate(value):
            html += f'<div class="input-row" style="margin-bottom: 8px; display: flex; align-items: center;">'
            html += f'<input type="text" value="{val}" style="width: 500px; margin-right: 8px;" class="text-input">'
            html += f'<button type="button" class="btn btn-sm btn-danger remove-input" style="padding: 2px 8px;"><i class="fas fa-times"></i></button>'
            html += '</div>'
        
        html += f'<div style="margin-bottom: 8px;">'
        html += f'<button type="button" id="{widget_id}_add" class="btn btn-sm btn-success" style="padding: 2px 8px;"><i class="fas fa-plus"></i> Add Key Allegation</button>'
        html += '</div>'
        html += '</div>'
        html += f'<input type="hidden" name="{name}" id="{widget_id}" value=\'{json.dumps(value)}\'>'
        
        html += f'''
        <script>
        (function() {{
            const container = document.getElementById('{widget_id}_container');
            const hiddenInput = document.getElementById('{widget_id}');
            const addBtn = document.getElementById('{widget_id}_add');
            
            function updateHidden() {{
                const inputs = container.querySelectorAll('.text-input');
                const values = Array.from(inputs).map(i => i.value.trim()).filter(v => v);
                hiddenInput.value = JSON.stringify(values);
            }}
            
            addBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                const row = document.createElement('div');
                row.className = 'input-row';
                row.style.marginBottom = '8px';
                row.innerHTML = '<input type="text" style="width: 500px; margin-right: 8px;" class="text-input"> <button type="button" class="btn btn-sm btn-danger remove-input" style="padding: 2px 8px;"><i class="fas fa-times"></i></button>';
                row.style.display = 'flex';
                row.style.alignItems = 'center';
                container.appendChild(row);
                
                row.querySelector('.remove-input').addEventListener('click', function() {{
                    row.remove();
                    updateHidden();
                }});
                
                row.querySelector('.text-input').addEventListener('input', updateHidden);
            }});
            
            container.addEventListener('click', function(e) {{
                if (e.target.classList.contains('remove-input')) {{
                    e.preventDefault();
                    e.target.parentElement.remove();
                    updateHidden();
                }}
            }});
            
            container.addEventListener('input', function(e) {{
                if (e.target.classList.contains('text-input')) {{
                    updateHidden();
                }}
            }});
        }})();
        </script>
        '''
        
        return mark_safe(html)
    
    def value_from_datadict(self, data, files, name):
        value = data.get(name, '[]')
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except:
            return []


class MultiTextField(Field):
    widget = MultiTextWidget
    
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
        if not value or len(value) < 1:
            raise ValidationError("At least one key allegation is required.")
    
    def prepare_value(self, value):
        if isinstance(value, list):
            return value
        return value
