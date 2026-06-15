import requests
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from requests.exceptions import HTTPError, JSONDecodeError
from langchain_openai import AzureChatOpenAI

def get_azure_chat_openai():
    # Key Vault URL
    key_vault_url = "https://fstodevazureopenai.vault.azure.net/"

# Authenticate using DefaultAzureCredential
    credential = DefaultAzureCredential()

# Create a SecretClient to interact with the Key Vault
    client = SecretClient(vault_url=key_vault_url, credential=credential)

# Secret names (make sure these secrets exist in your Key Vault)
    secret_names = ["llm-base-endpoint", "llm-mini", "llm-mini-version", "llm-api-key"]

# Retrieve secrets from the Key Vault with exception handling
    secrets = {}
    for secret_name in secret_names:
        try:
            secret = client.get_secret(secret_name)
            secrets[secret_name] = secret.value
        except Exception as e:
             print(f"Error retrieving secret '{secret_name}': {e}")
             raise
         
    try:
        base_url = secrets.get("llm-base-endpoint")  # Should be like https://fs-crewai-openai.openai.azure.com
        deployment = secrets.get("llm-mini")
        version = secrets.get("llm-mini-version")
        api_key = secrets.get("llm-api-key")

        if not all([base_url, deployment, version, api_key]):
            raise ValueError("One or more required secrets are missing.")
    except Exception as e:
        # Raise a clear error so callers know which secret failed
        raise RuntimeError(f"Failed to read Azure OpenAI secrets from Key Vault: {e}")

    # 5) Instantiate AzureChatOpenAI from langchain_openai
    llm = AzureChatOpenAI(
        azure_deployment=deployment,        # your deployment name
        openai_api_version=version,     # e.g., "2024-02-01-preview" or your configured API version
        azure_endpoint=base_url,            # full endpoint base e.g. "https://my-openai-instance.openai.azure.com"
        api_key=api_key,                    # subscription / API key
        streaming=False,                    # toggle streaming if you need it                    # adjust as desired
    )

    return llm


if __name__ == "__main__":
    from langchain_core.messages import HumanMessage
    llm = get_azure_chat_openai()
    resp = llm.invoke([HumanMessage(content="What's the capital of Canada?")])
    print(resp.content)