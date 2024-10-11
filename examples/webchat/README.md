# Beezle Bug Web Chat

## Installation 
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r examples/webchat/requirements.txt
```

# Running Server and Bot 
```bash
python -m examples.webchat.server
python -m examples.webchat.bot --name "Beezle Bug" --debug
```

Open a browser window at http://localhost:5000