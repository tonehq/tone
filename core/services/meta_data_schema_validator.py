from typing import Any


class MetaDataSchemaValidator:
    """Validates user-entered values against provider meta_data_schema constraints.

    Pure logic class — no DB dependency. Takes schema definitions and user values,
    returns structured errors.
    """

    @staticmethod
    def _get_validator_dict(field: dict) -> dict:
        """Safely get validator as a dict. Handles null and string values."""
        v = field.get("validator")
        return v if isinstance(v, dict) else {}

    def validate_required(self, name: str, value: Any, required: int) -> str | None:
        if required == 1 and (value is None or value == ""):
            return f"{name} is required"
        return None

    def validate_type(self, name: str, value: Any, data_type: str) -> str | None:
        if data_type == "float":
            try:
                float(value)
            except (TypeError, ValueError):
                return f"{name} must be a valid number"
        elif data_type in ("integer", "int"):
            try:
                val = int(value)
                if isinstance(value, float) and value != val:
                    return f"{name} must be a whole number"
            except (TypeError, ValueError):
                return f"{name} must be a whole number"
        elif data_type == "boolean":
            if not isinstance(value, bool):
                return f"{name} must be true or false"
        elif data_type == "string":
            if not isinstance(value, str):
                return f"{name} must be a string"
        elif data_type in ("array", "list"):
            if not isinstance(value, list):
                return f"{name} must be a list"
        return None

    def validate_range(self, name: str, value: Any, min_val: Any, max_val: Any) -> list[str]:
        errors = []
        try:
            num = float(value)
            if min_val is not None and num < float(min_val):
                errors.append(f"{name} must be at least {min_val}")
            if max_val is not None and num > float(max_val):
                errors.append(f"{name} must be at most {max_val}")
        except (TypeError, ValueError):
            pass  # Type validation handles this
        return errors

    def validate_options(self, name: str, value: Any, options: list | None) -> str | None:
        if not options:
            return None
        if value not in options:
            return f"{name} must be one of: {', '.join(str(o) for o in options)}"
        return None

    def validate_field(self, field_schema: dict, value: Any) -> list[str]:
        """Validate a single field value against its schema definition."""
        name = field_schema.get("name", "")
        required = field_schema.get("required", 0)
        data_type = field_schema.get("data_type", "")
        validator = self._get_validator_dict(field_schema)
        options = field_schema.get("options")

        # Required check
        req_err = self.validate_required(name, value, required)
        if req_err:
            return [req_err]

        # Skip remaining checks if value is None/empty and not required
        if value is None or value == "":
            return []

        # Type validation
        type_err = self.validate_type(name, value, data_type)
        if type_err:
            return [type_err]

        errors = []

        # Range validation (for numeric types)
        if data_type in ("float", "integer", "int"):
            errors.extend(self.validate_range(name, value, validator.get("min"), validator.get("max")))

        # Options validation (for select/dropdown fields)
        opt_err = self.validate_options(name, value, options)
        if opt_err:
            errors.append(opt_err)

        return errors

    def validate_settings(
        self, schema: list[dict], settings: dict,
        model_meta_data: dict | None = None,
    ) -> dict[str, list[str]]:
        """Validate all meta_data_schema fields in a settings dict.

        Args:
            schema: List of field definitions from ModelProvider.meta_data_schema[kind]
            settings: The user-submitted settings dict (e.g. llm_settings)
            model_meta_data: Optional model-level meta_data that overrides validator
                max for fields where the model defines a limit (e.g. max_completion_tokens)

        Returns:
            Dict of {field_name: [error_messages]}. Empty dict = all valid.
        """
        errors: dict[str, list[str]] = {}

        for field_schema in schema:
            field_name = field_schema.get("name")
            if not field_name:
                continue

            # Override validator max with model-level limit if present
            effective_schema = field_schema
            if model_meta_data and field_name in model_meta_data:
                effective_schema = dict(field_schema)
                validator = dict(self._get_validator_dict(field_schema))
                validator["max"] = model_meta_data[field_name]
                effective_schema["validator"] = validator

            value = settings.get(field_name)
            field_errors = self.validate_field(effective_schema, value)
            if field_errors:
                errors[field_name] = field_errors

        return errors
