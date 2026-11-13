#!/usr/bin/env python3

"""Agent entry point"""

import asyncio

from agent.cli import main


if __name__ == '__main__':
    asyncio.run(main())
