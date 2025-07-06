# Reasoning Visualization Agent

This implementation provides a complete solution for visualizing the reasoning process of an AI agent when making tool calls. It replaces the abstracted `create_react_agent` approach with a custom implementation that exposes the reasoning steps.

## Key Features

### 🧠 Reasoning Process Visualization
- **Step-by-step reasoning tracking**: Every decision and action is logged with timestamps
- **Tool usage analysis**: Shows why specific tools were chosen and their results
- **Timeline visualization**: Displays the reasoning process in a chronological timeline
- **Interactive follow-up**: Users can ask for more details about the reasoning process

### 🔧 Tool Integration
- **MCP tool support**: Works with any MCP (Model Context Protocol) tools
- **Real-time tool tracking**: Captures tool inputs, outputs, and execution times
- **Tool result analysis**: Shows how tool results influenced the final response

### 📊 Enhanced UI
- **Visual reasoning timeline**: Emoji-coded steps for easy understanding
- **Tool execution summary**: Detailed view of all tool calls and results
- **Interactive actions**: Buttons for exploring reasoning details and available tools

## How It Works

### 1. Reasoning Process Flow

```
User Question → Analysis → Tool Assessment → Execution → Response
     ↓              ↓            ↓            ↓          ↓
  Initial      Determine     Choose        Execute    Final
  Analysis     Tool Need     Tools         Tools      Response
```

### 2. Reasoning Steps Tracked

- **🔍 Analysis**: Initial understanding of the user's request
- **🤔 Tool Analysis**: Determining if tools are needed
- **⚙️ Tool Execution**: Starting tool-based processing
- **📋 Tool Selection**: Choosing appropriate tools
- **✅ Tool Used**: Successful tool execution
- **💭 Direct Response**: Generating response without tools
- **✨ Response Generation**: Creating the final answer
- **🎯 Completion**: Process completion

### 3. Tool Result Tracking

For each tool call, the system tracks:
- Tool name and description
- Input parameters
- Output results
- Execution timestamp
- Success/failure status

## Usage

### Running the Reasoning Agent

```bash
# Run the reasoning visualization agent
python reasoning_agent_demo.py
```

### Example Interaction

**User**: "Get me the latest foreign exchange transactions"

**Agent Reasoning Timeline**:
```
🧠 Step 1 (Analysis): Analyzing user request: Get me the latest foreign exchange transactions
⏱️ Time: 0.05s
📝 Starting analysis of user request

🤔 Step 2 (Tool Analysis): Tool need analysis: Tools needed
⏱️ Time: 0.12s
📝 Tool need analysis: Tools needed

⚙️ Step 3 (Tool Execution): Starting tool-based execution
⏱️ Time: 0.15s
📝 Starting tool-based execution

📋 Step 4 (Tool Selection): Available tools: ['GetForeignExchangeTransactionData', 'SearchDocuments']
⏱️ Time: 0.18s
📝 Available tools: ['GetForeignExchangeTransactionData', 'SearchDocuments']

✅ Step 5 (Tool Used): Successfully used tool 'GetForeignExchangeTransactionData'
⏱️ Time: 1.25s
📝 Successfully used tool 'GetForeignExchangeTransactionData'

🎯 Step 6 (Completion): Response generation completed
⏱️ Time: 1.45s
📝 Response generation completed
```

**Tool Execution Summary**:
```
🔧 Tool: GetForeignExchangeTransactionData
⏱️ Time: 1.20s
📊 Result: [Transaction data in JSON format...]
```

## Implementation Details

### Core Classes

#### `ReasoningTracker`
- Tracks reasoning steps and tool results
- Provides timestamps for performance analysis
- Logs all decision points

#### `ReasoningAgent`
- Main agent class that orchestrates the reasoning process
- Integrates with LangChain's tool calling
- Manages the complete reasoning workflow

### Key Methods

#### `process_message(user_message)`
- Main entry point for processing user messages
- Orchestrates the complete reasoning process
- Returns response with reasoning data

#### `_analyze_tool_need(user_message)`
- Analyzes if tools are needed based on keywords
- Uses heuristic analysis for tool selection
- Logs the decision-making process

#### `_execute_with_tools(user_message)`
- Executes tool-based responses
- Integrates with LangChain's AgentExecutor
- Tracks all tool usage and results

#### `_execute_direct_response(user_message)`
- Handles responses without tool usage
- Uses LLM directly for knowledge-based responses
- Tracks response generation process

### UI Components

#### `display_reasoning_visualization()`
- Creates the visual reasoning timeline
- Formats tool execution summaries
- Uses emojis for easy step identification

#### Action Callbacks
- `explain_reasoning`: Provides detailed reasoning explanation
- `show_tools`: Displays available tools
- `visualize_data`: Handles data visualization

## Benefits Over `create_react_agent`

### 1. Transparency
- **Before**: Abstracted reasoning process, only final output visible
- **After**: Complete reasoning timeline with decision points

### 2. Debugging
- **Before**: Difficult to understand why specific tools were chosen
- **After**: Clear reasoning for each tool selection and usage

### 3. User Experience
- **Before**: Users see only the final answer
- **After**: Users can follow the agent's thinking process

### 4. Performance Analysis
- **Before**: No visibility into execution times
- **After**: Detailed timing for each step and tool call

## Configuration

### MCP Server Setup
```python
multi_mcp_config = {
    "mcp1": {
        "url": "http://localhost:8001/mcp",
        "transport": "streamable_http",
    },
    "mcp2": {
        "url": "http://localhost:8002/mcp",
        "transport": "streamable_http",
    },
}
```

### System Prompt
The enhanced system prompt includes specific instructions for reasoning:
- Step-by-step reasoning requirements
- Tool usage guidelines
- Clear reasoning process structure

## Customization

### Adding New Reasoning Steps
```python
def add_custom_step(self, step_type: str, content: str):
    self.tracker.add_step(step_type, content)
```

### Custom Tool Analysis
```python
async def custom_tool_analysis(self, user_message: str) -> bool:
    # Add your custom logic here
    return needs_tools
```

### Enhanced Visualization
```python
async def custom_visualization(self, reasoning_steps, tool_results):
    # Add your custom visualization logic
    pass
```

## Troubleshooting

### Common Issues

1. **Tool not found**: Ensure MCP servers are running and accessible
2. **Reasoning steps not showing**: Check that the ReasoningTracker is properly initialized
3. **Performance issues**: Monitor timestamps to identify bottlenecks

### Debug Mode
Enable debug logging by setting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

1. **Reasoning Analytics**: Track reasoning patterns over time
2. **Performance Optimization**: Identify and optimize slow reasoning steps
3. **Custom Visualizations**: Add charts and graphs for reasoning analysis
4. **Reasoning Templates**: Predefined reasoning patterns for common tasks
5. **Collaborative Reasoning**: Multiple agents working together with shared reasoning

## Conclusion

This reasoning visualization implementation provides complete transparency into the AI agent's decision-making process. It transforms the black-box nature of `create_react_agent` into a transparent, debuggable, and user-friendly system that shows exactly how and why the agent makes its decisions. 