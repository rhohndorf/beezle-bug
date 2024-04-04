### Environment Interaction via Tool Use/Discovery/Generation
Tools are the interface by which Beezle Bug interacts with its environment and controls its internal mechanisms.

A tool is a function or a pydantic object that can be selected and executed by an agent.

The first version of Beezle Bug will have a predefined set of tools for
* user interaction (send messages, read messages from input buffer/chat room)
* filesystem interaction (read/write files, list directories)
* memory interaction (provided by llama-cpp-agent)
* web search and website scraping

At some point tools will be added for 
* task management (discovery,decomposition, aggregation,...)
* agent interaction

Later on tools for automatic tool discovery and generation will be added.
* tool for writing new tools
* tools for combining existing tools into a new tool

### User interaction
In the beginning the only way to interact with the agent will be via a text interface.
Later we will add speech-to-text input and text-to-speech output.
In any case user input is stored in an input buffer queue that can be accessed by the agent via a tool and if the agent wants to output a message to the user it executes a "send message" tool.