## Farmo – the LLM-based assistant for Farmely (hehe)

### Setup

Create a Python virtual environment (Python > 3.10; tested with 3.12):

```shell
python -m venv .env
```

Create an environment variable file (`.env_vars`) with the following content:

```
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="YOUR_KEY_HERE"
LANGSMITH_PROJECT="YOUR_PROJECT_HERE"
OPENAI_API_KEY="YOU_GOT_IT: YOUR_KEY_HERE"
```

Install all requirements:

```shell
pip install -r requirements.txt
```

### Initialize

You have to initalize the databases. Just run the files and it will create the sqlite dbs.

```python
python rag_factory.py
```
```python
python user_db.py
```


### Test

To test via CLI:

```shell
python assistant.py
```

To test via UI app:

```shell
streamlit run app.py
```

To test via API
```shell
python api.py
```

### Product RAG
To use the products you need to fetch from the API. Afterwars you can process them by executing "farmely_data_clean" and "farmely_data_clean_postprocessing_german" to translate the fields into speaking german names. Then you transfer the products from json to markdown. Just execute "json_to_markdown.py". Finally, you execute the rag_factory. The embedding might take a few seconds.
