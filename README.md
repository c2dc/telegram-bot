# Telegram bot

To install and run the program,

```python
poetry install
poetry run python main.py
```

Also, make sure there is a `config.yaml` in the root folder with the following template.

```yaml
db_password: xxxxxxx
# Telethon credentials
api_id: 000000
api_hash: 000000000000000000000000000000
# Twarc2 credentials
consumer_key: xxxxxxx
consumer_secret: xxxxxxx
```