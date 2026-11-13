# Custom Agent loop

Install dependencies and the package (editable) first:
```
uv venv
uv pip install -e .
```

Run the agent:
```
python -m agent --session_id test
```

- `--session_id` is optional. Without it the latest saved session is resumed,
  or a new one is started when none exist.
- Type `/new` to start a fresh session, `exit` or `quit` to stop.
- A message may span several lines; finish it with an empty line.
