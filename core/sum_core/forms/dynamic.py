"""
Name: Dynamic form generation
Path: core/sum_core/forms/dynamic.py
Purpose: Generate Django forms from FormDefinition StreamField blocks at runtime.
Family: Forms, Dynamic Forms foundation.
Dependencies: Django forms, FormDefinition fields.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from django import forms

try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

logger = logging.getLogger(__name__)

FORM_CLASS_CACHE_TTL_SECONDS = 3600
# In-process cache: not shared across workers or persisted across restarts.
_FORM_CLASS_CACHE: dict[str, tuple[float, type[forms.Form]]] = {}

# MIME type mapping for common file extensions
# Maps file extensions to expected MIME types for validation
# Note: Modern Office "x" formats (e.g. .docx, .xlsx, .pptx) are ZIP archives,
# so application/zip is also accepted for those extensions.
# Text-based formats include common MIME type variants/aliases.
EXTENSION_TO_MIME_TYPES = {
    ".pdf": ["application/pdf"],
    ".doc": ["application/msword"],
    ".docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    ],
    ".xls": ["application/vnd.ms-excel"],
    ".xlsx": [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    ],
    ".ppt": ["application/vnd.ms-powerpoint"],
    ".pptx": [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",
    ],
    ".txt": [
        "text/plain",
        "text/plain; charset=utf-8",
        "text/plain; charset=us-ascii",
    ],
    ".csv": [
        "text/csv",
        "text/plain",
        "application/csv",
        "text/comma-separated-values",
        "application/vnd.ms-excel",  # Excel sometimes opens CSVs
    ],
    ".jpg": ["image/jpeg"],
    ".jpeg": ["image/jpeg"],
    ".png": ["image/png"],
    ".gif": ["image/gif"],
    ".bmp": ["image/bmp", "image/x-ms-bmp"],
    ".tiff": ["image/tiff"],
    ".tif": ["image/tiff"],
    ".svg": ["image/svg+xml", "application/xml", "text/xml"],
    ".webp": ["image/webp"],
    ".zip": ["application/zip", "application/x-zip-compressed"],
    ".rar": ["application/x-rar-compressed", "application/vnd.rar"],
    ".7z": ["application/x-7z-compressed"],
    ".tar": ["application/x-tar"],
    ".gz": ["application/gzip", "application/x-gzip"],
    ".mp3": ["audio/mpeg"],
    ".wav": ["audio/wav", "audio/x-wav"],
    ".mp4": ["video/mp4"],
    ".avi": ["video/x-msvideo"],
    ".mov": ["video/quicktime"],
    ".webm": ["video/webm"],
    ".json": [
        "application/json",
        "text/json",
        "text/plain",  # JSON often detected as plain text
    ],
    ".xml": ["application/xml", "text/xml"],
}


def _validate_mime_type(uploaded_file, allowed_extensions: list[str]) -> str | None:
    """
    Validate file's actual MIME type matches its extension.

    Args:
        uploaded_file: Django UploadedFile object
        allowed_extensions: List of allowed file extensions (e.g., ['.pdf', '.doc'])

    Returns:
        Error message if validation fails, None if validation passes
    """
    if not MAGIC_AVAILABLE:
        # python-magic not installed, skip MIME validation
        # This is defense-in-depth, so we gracefully degrade
        return None

    if not allowed_extensions:
        return None

    # Get the file extension
    original_name = uploaded_file.name or ""
    _, file_ext = os.path.splitext(original_name)
    file_ext = file_ext.lower()

    if file_ext not in allowed_extensions:
        # Extension already checked elsewhere, skip MIME check
        return None

    # Get expected MIME types for this extension
    expected_mimes = EXTENSION_TO_MIME_TYPES.get(file_ext, [])
    if not expected_mimes:
        # Extension not in our MIME mapping, allow through
        # This handles custom/uncommon file types
        return None

    # Read file content for MIME detection
    try:
        # Read first 2KB for MIME type detection
        uploaded_file.seek(0)
        file_header = uploaded_file.read(2048)
        uploaded_file.seek(0)  # Reset file pointer

        if not file_header:
            return "File appears to be empty."

        # Detect MIME type from file content
        try:
            detected_mime = magic.from_buffer(file_header, mime=True)
        except AttributeError as e:
            # The magic module does not provide from_buffer as expected
            # This is a programming/configuration error that should be raised
            logger.error(
                "python-magic appears to be misconfigured or an unexpected version is installed: "
                f"missing 'from_buffer' for {original_name}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            # python-magic not properly installed or configured
            # This includes magic.MagicException and other runtime errors
            logger.warning(
                f"MIME detection failed for {original_name}: {e}. "
                "This may indicate python-magic or libmagic is not properly installed. "
                "Skipping MIME validation."
            )
            return None

        # Check if detected MIME matches expected MIME types
        if detected_mime not in expected_mimes:
            # User-friendly error message with detected MIME type for debugging
            logger.info(
                f"MIME mismatch for {original_name}: expected {expected_mimes}, "
                f"got {detected_mime}"
            )
            expected_display = ", ".join(expected_mimes)
            return (
                f"File content appears to be '{detected_mime}', but expected {expected_display} "
                f"for '{file_ext}' files. Please ensure you're uploading the correct file type."
            )

    except OSError as e:
        # File read error
        logger.warning(
            f"Could not read file {original_name} for MIME validation: {e}. "
            "Skipping MIME validation."
        )
        return None
    except Exception as e:
        # Unexpected error - log but don't block upload
        logger.error(
            f"Unexpected error during MIME validation for {original_name}: {e}",
            exc_info=True,
        )
        return None

    return None


def _file_validation_clean(form_instance):
    cleaned = forms.Form.clean(form_instance)
    file_validation_rules = getattr(form_instance, "_file_validation_rules", {}) or {}
    for field_name, rule in file_validation_rules.items():
        uploaded = cleaned.get(field_name)
        if not uploaded:
            continue

        errors = []
        extensions = rule.get("extensions") or []
        max_size_bytes = rule.get("max_size_bytes")
        max_size_mb = rule.get("max_size_mb")

        if extensions:
            original_name = uploaded.name or ""
            _, original_ext = os.path.splitext(original_name)
            ext = original_ext.lower()
            if ext not in extensions:
                errors.append(
                    f"File type '{original_ext or 'unknown'}' " "is not allowed."
                )

        if max_size_bytes and uploaded.size > max_size_bytes:
            max_size_mb_display = max_size_mb
            if not max_size_mb_display and max_size_bytes:
                max_size_mb_display = max_size_bytes / (1024 * 1024)
            errors.append(f"File must be {max_size_mb_display:g}MB or smaller.")

        # Validate MIME type matches extension (defense-in-depth)
        if extensions:
            mime_error = _validate_mime_type(uploaded, extensions)
            if mime_error:
                errors.append(mime_error)

        for message in errors:
            form_instance.add_error(field_name, message)

    return cleaned


class DynamicFormGenerator:
    """
    Generates Django Form classes from FormDefinition at runtime.

    Usage:
        generator = DynamicFormGenerator(form_definition)
        FormClass = generator.generate_form_class()
        form = FormClass(data=request.POST, files=request.FILES)
    """

    def __init__(self, form_definition) -> None:
        self.form_definition = form_definition

    def generate_form_class(self):
        """Returns a Django Form class with fields from FormDefinition."""
        cache_key = self._get_cache_key()
        if cache_key:
            cached = _FORM_CLASS_CACHE.get(cache_key)
            if cached:
                cached_at, form_class = cached
                if time.time() - cached_at < FORM_CLASS_CACHE_TTL_SECONDS:
                    return form_class
                _FORM_CLASS_CACHE.pop(cache_key, None)

        fields: dict[str, forms.Field] = {}
        file_rules: dict[str, dict[str, Any]] = {}

        for block in self.form_definition.fields:
            mapped = self._map_block_to_field(block.block_type, block.value)
            if mapped is None:
                continue
            field_name, field, file_rule = mapped
            fields[field_name] = field
            if file_rule:
                file_rules[field_name] = file_rule

        attrs: dict[str, Any] = {"__module__": __name__}
        attrs.update(fields)
        attrs["_file_validation_rules"] = file_rules
        attrs["form_definition"] = self.form_definition
        attrs["clean"] = _file_validation_clean

        suffix = self.form_definition.pk or "Runtime"
        form_class = type(f"DynamicForm{suffix}", (forms.Form,), attrs)

        if cache_key:
            _FORM_CLASS_CACHE[cache_key] = (time.time(), form_class)

        return form_class

    def _map_block_to_field(self, block_type, block_value):
        """Maps a FormFieldBlock to a Django form field."""
        if block_type in {"section_heading", "help_text"}:
            return None

        field_name = block_value.get("field_name")
        label = block_value.get("label", "")
        help_text = block_value.get("help_text", "")
        required = bool(block_value.get("required", True))
        widget_attrs = self._build_widget_attrs(block_type, block_value)

        if block_type == "text_input":
            field = forms.CharField(
                label=label,
                required=required,
                help_text=help_text,
                max_length=block_value.get("max_length"),
                widget=forms.TextInput(
                    attrs=self._apply_placeholder(block_value, widget_attrs)
                ),
            )
            return field_name, field, None

        if block_type == "email_input":
            field = forms.EmailField(
                label=label,
                required=required,
                help_text=help_text,
                max_length=block_value.get("max_length"),
                widget=forms.EmailInput(
                    attrs=self._apply_placeholder(block_value, widget_attrs)
                ),
            )
            return field_name, field, None

        if block_type == "phone_input":
            attrs = self._apply_placeholder(block_value, widget_attrs)
            format_mask = block_value.get("format_mask")
            if format_mask:
                attrs["data-format-mask"] = format_mask
            field = forms.CharField(
                label=label,
                required=required,
                help_text=help_text,
                widget=forms.TextInput(attrs=attrs),
            )
            return field_name, field, None

        if block_type == "textarea":
            attrs = self._apply_placeholder(block_value, widget_attrs)
            rows = block_value.get("rows")
            if rows:
                attrs["rows"] = rows
            field = forms.CharField(
                label=label,
                required=required,
                help_text=help_text,
                max_length=block_value.get("max_length"),
                widget=forms.Textarea(attrs=attrs),
            )
            return field_name, field, None

        if block_type == "select":
            choices = self._extract_choices(block_value.get("choices"))
            allow_multiple = bool(block_value.get("allow_multiple", False))
            if allow_multiple:
                field = forms.MultipleChoiceField(
                    label=label,
                    required=required,
                    help_text=help_text,
                    choices=choices,
                    widget=forms.SelectMultiple(attrs=widget_attrs),
                )
            else:
                field = forms.ChoiceField(
                    label=label,
                    required=required,
                    help_text=help_text,
                    choices=choices,
                    widget=forms.Select(attrs=widget_attrs),
                )
            return field_name, field, None

        if block_type == "checkbox":
            attrs = dict(widget_attrs)
            checked_value = block_value.get("checked_value")
            if checked_value:
                attrs["value"] = checked_value
            field = forms.BooleanField(
                label=label,
                required=required,
                help_text=help_text,
                widget=forms.CheckboxInput(attrs=attrs),
            )
            return field_name, field, None

        if block_type == "checkbox_group":
            field = forms.MultipleChoiceField(
                label=label,
                required=required,
                help_text=help_text,
                choices=self._extract_choices(block_value.get("choices")),
                widget=forms.CheckboxSelectMultiple(attrs=widget_attrs),
            )
            return field_name, field, None

        if block_type == "radio_buttons":
            field = forms.ChoiceField(
                label=label,
                required=required,
                help_text=help_text,
                choices=self._extract_choices(block_value.get("choices")),
                widget=forms.RadioSelect(attrs=widget_attrs),
            )
            return field_name, field, None

        if block_type == "file_upload":
            max_size_mb = block_value.get("max_file_size_mb")
            if max_size_mb is not None and max_size_mb > 0:
                max_size_bytes = max_size_mb * 1024 * 1024
            else:
                max_size_bytes = None
            file_rule = {
                "extensions": self._normalize_extensions(
                    block_value.get("allowed_extensions", "")
                ),
                "max_size_bytes": max_size_bytes,
                "max_size_mb": max_size_mb,
            }
            field = forms.FileField(
                label=label,
                required=required,
                help_text=help_text,
                widget=forms.ClearableFileInput(attrs=widget_attrs),
            )
            return field_name, field, file_rule

        return None

    def _build_widget_attrs(self, block_type, block_value) -> dict[str, str]:
        attrs: dict[str, str] = {}
        base_classes = self._default_widget_classes(block_type)
        css_class = block_value.get("css_class")
        combined = " ".join(
            value for value in [base_classes, css_class] if value
        ).strip()
        if combined:
            attrs["class"] = combined
        return attrs

    def _apply_placeholder(self, block_value, attrs: dict[str, str]) -> dict[str, str]:
        placeholder = block_value.get("placeholder")
        if placeholder:
            attrs = dict(attrs)
            attrs["placeholder"] = placeholder
        return attrs

    def _default_widget_classes(self, block_type) -> str:
        base_input = (
            "w-full bg-transparent border-0 border-b-2 border-sage-black/20 "
            "py-3 text-lg font-body text-sage-black placeholder-sage-black/40 "
            "focus:border-sage-terra focus:ring-0 transition-colors"
        )
        base_textarea = (
            "w-full bg-transparent border-0 border-b-2 border-sage-black/20 "
            "py-3 text-lg font-body text-sage-black placeholder-sage-black/40 "
            "focus:border-sage-terra focus:ring-0 transition-colors resize-y"
        )
        base_select = (
            "w-full bg-transparent border-0 border-b-2 border-sage-black/20 "
            "py-3 text-lg font-body text-sage-black focus:border-sage-terra "
            "focus:ring-0 transition-colors cursor-pointer"
        )
        base_checkbox = (
            "h-4 w-4 rounded border-sage-black/30 text-sage-terra "
            "focus:ring-sage-terra"
        )
        base_file = (
            "block w-full text-sm text-sage-black file:mr-4 file:rounded-none "
            "file:border-0 file:bg-sage-terra/10 file:px-4 file:py-2 "
            "file:font-body file:text-xs file:uppercase file:tracking-widest "
            "file:text-sage-black hover:file:bg-sage-terra/20"
        )
        base_group = "space-y-3"

        return {
            "text_input": base_input,
            "email_input": base_input,
            "phone_input": base_input,
            "textarea": base_textarea,
            "select": base_select,
            "checkbox": base_checkbox,
            "checkbox_group": base_group,
            "radio_buttons": base_group,
            "file_upload": base_file,
        }.get(block_type, "")

    def _extract_choices(self, choices_value) -> list[tuple[str, str]]:
        if not choices_value:
            return []
        choices = []
        for choice in choices_value:
            value = getattr(choice, "value", choice)
            choices.append((value["value"], value["label"]))
        return choices

    def _normalize_extensions(self, raw_extensions: str) -> list[str]:
        if not raw_extensions:
            return []
        normalized = []
        for raw in raw_extensions.split(","):
            ext = raw.strip().lower()
            if not ext:
                continue
            if not ext.startswith("."):
                ext = f".{ext}"
            normalized.append(ext)
        return normalized

    def _get_cache_key(self) -> str | None:
        form_definition = self.form_definition
        form_id = getattr(form_definition, "pk", None) or getattr(
            form_definition, "id", None
        )
        updated_at = getattr(form_definition, "updated_at", None)
        if not form_id or not updated_at:
            return None
        try:
            updated_stamp = f"{updated_at.timestamp():.6f}"
        except (TypeError, ValueError):
            return None
        return f"dynamic_form_class:{form_id}:{updated_stamp}"
