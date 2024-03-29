# Beezle Bug
In the [Otherland](https://en.wikipedia.org/wiki/Otherland) series of cyberpunk novels Beezle Bug is the virtual assistant of Orlando Gardiner, one of the main characters.
Originally a kids' toy, it was upgraded many times until it's almost as sentient as a real person.
Beezle Bug has two different forms of appearance. In the virtual world it appears as a creature with many arms and legs. It can also download itself into a spider-like toy robot in the physical world.


* [Vision and Goals](#vision)
* [Current State](#current_state)
* [Resources](#resources)

## Vision and Goals
Like its fictional counterpart our Beezle Bug agent starts as a limited toy project and will hopefully grow into a useful tool over time.

With Beezle Bug we want to explore agentive behaviours like
* Autonomy
* Cooperation
* Self Improvement

### Autonomy, Proactivity and Continuity
Beezle Bug will be an autonomous, continuosly running and proactive agent. 

This means it will e.g.
* Run permanently and decide what to do next
* Manage its memory
* Execute long running tasks in the background
* Yield execution if there's nothing to do
* Start additional instances of itself

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

### Task Decomposition and Delegation
The main agent may decide to break an identified task down into a number of subtasks and either work on them sequentially or start a number of (specialized) agents.

## Current State
No code is available as of yet.

## Resources

