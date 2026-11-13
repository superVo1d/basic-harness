#!/usr/bin/env python3

"""CLI entry point"""

import argparse
import asyncio

from agent.session import Session, latest_session_id
from agent.loop import run_agent
from agent.logging_setup import configure_logging


EXAMPLE_USER_TASK = '''
Спланируй поездку в Казань на 3 дня. Разбей на отдельные задачи: выбрать билеты,
забронировать отель, составить маршрут на каждый день, выбрать 3 места поесть,
посчитать бюджет, собрать список вещей. Заведи список задач и веди его по ходу дела:
перед каждым шагом ставь задачу in_progress, после — completed. В конце прочитай
список и покажи, что осталось несделанным.
'''


def read_message() -> str:
    """Read a message. Commands start with '/' and exit/quit are one line;
    anything else may span several lines — an empty line sends it."""
    first = input('\n> ').strip()
    if not first or first.lower() in ('exit', 'quit') or first.startswith('/'):
        return first

    lines = [first]
    while True:
        try:
            nxt = input('... ')
        except EOFError:
            break
        if not nxt.strip():
            break
        lines.append(nxt)
    return '\n'.join(lines).strip()


async def main():
    """Start a new agent."""
    configure_logging()

    parser = argparse.ArgumentParser()

    parser.add_argument("--session_id", type=str,
                        help="Your session ID (optional flag)")

    args = parser.parse_args()

    session_id = args.session_id
    if session_id is None:
        session_id = latest_session_id()
        if session_id:
            print(f"Resuming latest session: {session_id}")

    session = Session(_id=session_id)
    if await session.load():
        print(f"Loaded session with ID: {session.id}")
    else:
        print(f"Started new session with ID: {session.id}")

    print('Assistant: Ask me something complex!')

    while True:
        user_msg = read_message()
        if not user_msg:
            continue
        print(f'User: {user_msg}')
        if user_msg.lower() in ('exit', 'quit'):
            break
        if user_msg.lower() == '/new':
            session.reset()
            print('Assistant: Ask me something complex!')
            continue
        if user_msg.startswith('/goal'):
            goal = user_msg[len('/goal'):].strip()
            if not goal:
                print('Usage: /goal <task>')
                continue
            session.goal = goal
            session.add({'role': 'user', 'content': goal})
        else:
            session.add({'role': 'user', 'content': user_msg})
        assistant_msg = run_agent(session)
        await session.save()
        print(f'\nAssistant: {assistant_msg}')


if __name__ == '__main__':
    asyncio.run(main())
