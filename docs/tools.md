# Tools
Tools are the interface by which Beezle Bug interacts with its environment and controls its internal mechanisms.

A tool is a pydantic object that can be selected and executed by an agent.

Beezle Bug has a predefined set of tools for
* user interaction (send messages, read messages from input buffer/chat room)
* filesystem interaction (read/write files, list directories)
* memory interaction
* web search and website scraping

At some point tools will be added for 
* task management (discovery,decomposition, aggregation,...)
* agent interaction

Later on tools for automatic tool discovery and generation will be added.
* tool for writing new tools
* tools for combining existing tools into a new tool

