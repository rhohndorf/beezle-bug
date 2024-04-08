# Memory Management
Beezle Bug has two forms of memory:
* the Working Memory
* the Memory Stream

## Working Memory
The working memory is a key value scratch buffer for the agent. The agent can add, update or delete eintries.

## Memory Stream
The Memory Stream consists of events recorded by the agent. Examples of this are the user sending a message
and the agent selecting a tool and executing it.
The memory stream has a fixed size window that is inserted into the LLMs context. This means only the last n events are displayed. Older memories can be retrieved and inserted back into the context window by the agent by using the Recall tool.
