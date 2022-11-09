# telegram-bot

This project aims to develop a command line interface program to download all the relevant data from joined Telegram's groups and chats.

In order to do that, we heavily rely on Telethon library to interface with Telegram's official APIs. You can read more about its usage in [their docs](https://docs.telethon.dev/en/stable/).

## Summary 

<!--ts-->
  * [Installation](#installation)
  * [Running the code](#running)
    * [List all chats](#list-all)
    * [Download everything](#download-all)
    * [Download only text](#download-chats)
    * [Download only users](#download-users)
    * [Download only past media](#download-media)
    * [Download only grous/channels](#download-channels)
  * [Searching for invite links](#search)
    * [Twitter's method](#search-twitter)
    * [Telegram's method](#search-telegram)
  * [Export collected data](#export)
  * [Related work](#related-work)
<!--te-->

## Installation<a name="installation"></a>

Before installing, you must first edit `docker-compose.yml` and `config/config.yaml` to provide the necessary credentials for the application. In order for everything to work, you should supply

- Pgadmin credentials (optional)
- Postgres database credentials 
- Telegram API credentials
- Twitter API credentials (optional)

Then, you must initialize the necessary infrastructure and virtual environment.

```bash
docker-compose up -d
poetry install
poetry run alembic upgrade head
```


## Running the code<a name="running"></a>

This program implements several functionalities. You can check the most up to date ones by typing `poetry run python main.py --help`.

By default, it runs on every joined group and chat. If you want to change that behavior, specify in the `config/config.yaml` file a `whitelist` or a `blacklist`.

### List all chats<a name="list-all"></a>

To list all joined groups and channels, along with their ID, type

```bash
poetry run python main.py --list-dialogs
```

### Download everything<a name="download-all"></a>

To download channels, users, messages and media from joined groups and channels, type
```bash
poetry run python main.py
```

### Download only text<a name="download-chats"></a>
To download only messages from joined groups and channels, in order to speed up the process, type
```bash
poetry run python main.py --without-media
```

### Download only users<a name="download-users"></a>
To download only users from joined groups and channels, type
```bash
poetry run python main.py --get-participants
```

### Download only past media (WIP)<a name="download-media"></a>
To download only media from already seen messages, type
```bash
poetry run python main.py --download-past-media
```

### Download only groups/channels<a name="download-channels"></a>
> TO BE IMPLEMENTED

## Searching for invite links<a name="search"></a>

In order to enumerate channels and groups to join, there are three strategies available:
- **Manual search**: manually search in the web for available invite links. Any channel/group joined through the official app will be shown next time you run this code.
- **Twitter search**: use twarc2 to automate the search for invite links in old tweets
- **Telegram/Messages search**: use the acquired Telegram messages to search for invite links

For now, every valid invite link found with the automated methods will be joined, without the option of manual approval by the user.

### Twitter's method<a name="search-twitter"></a>

You can change the queries used to search twitter by modifying the [search_queries.txt](config/search_queries.txt) file.

```bash
poetry run python main.py --search-twitter
```
### Telegram's method (WIP) <a name="search-telegram"></a>
```bash
poetry run python main.py --search-messages
```

## Export collected data<a name="export"></a>
> TO BE IMPLEMENTED

## Related work<a name="related-work"></a>

These are two related repositories that heavily inspired the developing of telegram-bot.

- [pushshift/telegram](https://github.com/pushshift/telegram)
- [expectocode/telegram-export](https://github.com/expectocode/telegram-export) (archived)


