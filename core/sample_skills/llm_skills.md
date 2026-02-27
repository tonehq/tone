# To prepare meta data schema for LLM

Do the following scenario for LLM service providers:

The meta_data_schema defines the configuration fields required by a service provider.
Each field in the schema follows this structure:

{
  name: <key name>,
  type: <data type>,
  format: <format>,
  validator: <name of the validation function>,
  required: <0 or 1>,
  description: <description of the key>
}

A single service provider can have multiple schema fields.
For example, an LLM provider may require more fields than just model_name.

Only the schema definitions (not the actual values) should be stored in the service provider under meta_data_schema.
The actual values will be stored separately in agent_config.

Your task is to create this meta_data_schema for each service provider using the information in llm_meta_data_schema.yaml.
For fields that are required by the service provider, set required to 0; otherwise, set it to 1.

Update the meta_data_schema for each LLM service_provider in dev-data.json file where the values for seeding the service_provider is available.