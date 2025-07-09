from assistant.agent import Agent
from assistant.agent_config import AgentConfig
from assistant.utils.env_check import load_and_check_env

# Set up environment
"""
We need to load and check the environment variables before using the Agent.
This ensures that all required configurations are in place.
This is typically done at the start of the application to avoid runtime errors.
You dont need to do this explictly in your code, as it is already handled in the agent module.
We only show it here for clarity and completeness.
"""
load_and_check_env()

"""
The Env-Checker asks for the required environment variables and checks if they are set.
You can also set a .env_vars file in the root directory of your project.
This file should contain the environment variables in the format:
```
VAR_NAME=value
VAR_NAME2=value2
``` 
You find all required environment variables in the `assistant/required_env_vars.txt` file.
For the databases we use the pattern {DB_TYPE}_USER, {DB_TYPE}_PASSWORD, {DB_TYPE}_HOST, {DB_TYPE}_DB.
For example, for a PostgreSQL database you need to set the following environment variables:
```
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_DB=your_database
```
"""
# Initialize the Agent with the default configuration
agent_config = AgentConfig.as_default()
"""
The agent needs a configuration object to work.
You can use the default configuration or create your own.
Its important to understand that design choices are specified in the configuration. Sensible informations are set as environment variables.
You can also create a custom configuration by passing a dictionary to the AgentConfig constructor.

The default is currently:
{
    "name": "DefaultAgent",
    "description": "This is a default agent configuration.",
    "llm_provider": "openai",
    "llm_model": "gpt-4o-mini",
    "user_db": "postgres",
    "checkpoint_type": "postgres",
    "rag_db": "chroma",
}
"""

agent = Agent(config=agent_config)
"""
The Agent is the main class that handles the interaction with the user and the tools.
Its pretty straight forward to use. It has one entry point: the `chat` method. 
It works stateless. The history is saved in the database. Identified by the thread_id
The thread_id contains is a {user_id}-{uuid} format.
If no user_id is provided, it will use the anonymous user.
"""
content = {
    "msg": "Hallo, wie kann ich dir helfen?",
    "images": [],
    "barcode": "4016249010201" # Example barcode, you can remove this if not needed
}
user = {
    "user_id": None,
    "thread_id": None,
}