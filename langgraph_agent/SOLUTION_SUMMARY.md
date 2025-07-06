I'll explain all the functions and parts involved in generating the reasoning in the agent. Let me break down the entire flow:

Read file: langgraph_agent/agent_with_reasoning.py
Now let me read the main message handling function to see the complete flow:

Read file: langgraph_agent/agent_with_reasoning.py
Now I have a complete understanding of the reasoning generation system. Let me explain all the functions and parts involved:

## **Complete Reasoning Generation System Explanation**

### **1. System-Level Reasoning Instructions**

**Location**: `SYSTEM_PROMPT` (lines 30-50)
```python
**IMPORTANT: Always include a reasoning section in your response**
After providing your main answer, always include a "REASONING:" section that explains:
1. Tool Selection Reasoning: Show the chain of thought for selection of tool, based on the user's query
2. If you didn't use tools, explain why they weren't needed
3. What information sources you relied on for your response
4. Any assumptions or limitations in your reasoning
```

**Purpose**: This is the foundational instruction that tells the AI model to always include reasoning in its responses.

### **2. Context Enhancement Functions**

#### **A. `enhance_message_with_context()`** (lines 105-132)
**Purpose**: Adds reasoning instructions when search tools are used
```python
def enhance_message_with_context(messages, extracted_context, document_urls):
    # Adds a system message with:
    "Remember to include a 'REASONING:' section explaining that you used a search tool 
     to find relevant information and what sources you consulted."
```

#### **B. `enhance_tool_context_json()`** (lines 133-170)
**Purpose**: Adds reasoning instructions for FX transaction data
```python
def enhance_tool_context_json(messages):
    # Adds a system message with:
    "Remember to include a 'REASONING:' section explaining that you used the 
     GetForeignExchangeTransactionData tool to retrieve transaction data and why 
     this tool was necessary for the user's request."
```

#### **C. `add_direct_response_reasoning()`** (lines 171-183)
**Purpose**: Adds reasoning instructions when no tools are used
```python
def add_direct_response_reasoning(messages):
    # Adds a system message with:
    "Remember to include a 'REASONING:' section explaining why no tools were needed 
     for this response. Mention that you're relying on your training data and 
     general knowledge to answer this question."
```

### **3. Reasoning Extraction Function**

#### **`extract_reasoning_from_response()`** (lines 184-209)
**Purpose**: Extracts the reasoning section from AI responses using substring extraction
```python
def extract_reasoning_from_response(response_content):
    # Primary marker: "REASONING:"
    # Fallback markers: ["Reasoning:", "�� Reasoning:", "🤔", "💭"]
    # Returns everything from the marker to the end of the response
```

### **4. Main Message Processing Flow**

The reasoning generation happens in the `main()` function (lines 264-440) through **4 different response paths**:

#### **Path 1: Follow-up Questions** (lines 320-355)
```python
if is_followup:
    # 1. Add reasoning instruction to system message
    enhanced_messages.append({
        "role": "system",
        "content": "Remember to include a 'REASONING:' section explaining that you're reusing previous tool data..."
    })
    
    # 2. Generate response with reasoning
    final_response = await agent.ainvoke({"messages": enhanced_messages})
    
    # 3. Extract reasoning from response
    reasoning = extract_reasoning_from_response(response_content)
    
    # 4. Display reasoning in step output
    step.output = f"Response generated using previous context!\n\nREASONING:\n{reasoning}"
```

#### **Path 2: Direct Responses** (lines 356-371)
```python
elif not full_messages:
    # 1. Add reasoning instructions for direct response
    enhanced_messages = add_direct_response_reasoning(message_history.copy())
    
    # 2. Generate response with reasoning
    final_response = await agent.ainvoke({"messages": enhanced_messages})
    
    # 3. Extract and display reasoning
    reasoning = extract_reasoning_from_response(response_content)
    step.output = f"Response generated with reasoning!\n\nREASONING:\n{reasoning}"
```

#### **Path 3: FX Tool Responses** (lines 372-391)
```python
if fx_tool_message:
    # 1. Add FX-specific reasoning instructions
    system_message = enhance_tool_context_json(full_messages)
    enhanced_messages.append(system_message)
    
    # 2. Generate response with reasoning
    final_response = await agent.ainvoke({"messages": enhanced_messages})
    
    # 3. Extract and display reasoning
    reasoning = extract_reasoning_from_response(response_content)
    step.output = f"Response generated with FX table context!\n\nREASONING:\n{reasoning}"
```

#### **Path 4: Other Tool Responses** (lines 392-415)
```python
else:
    # 1. Extract tool context and add reasoning instructions
    enhanced_messages = enhance_message_with_context(message_history, extracted_context, document_urls)
    
    # 2. Generate response with reasoning
    final_response = await agent.ainvoke({"messages": enhanced_messages})
    
    # 3. Extract and display reasoning
    reasoning = extract_reasoning_from_response(response_content)
    step.output = f"Response generated with enhanced context!\n\nREASONING:\n{reasoning}"
```

### **5. How the Reasoning Generation Works**

#### **Step-by-Step Process**:

1. **User sends message** → `main()` function is triggered

2. **Initial agent call** → Agent decides whether to use tools or respond directly

3. **Response path determination** → Based on tool usage, one of 4 paths is chosen

4. **Reasoning instruction injection** → Appropriate reasoning instructions are added to the message context

5. **Final response generation** → Agent generates response including the reasoning section

6. **Reasoning extraction** → `extract_reasoning_from_response()` extracts the reasoning part

7. **Step output display** → Reasoning is displayed in the Chainlit step output

#### **Key Components**:

- **System Prompt**: Foundation instruction for reasoning
- **Context Enhancement Functions**: Add specific reasoning instructions based on response type
- **Extraction Function**: Pulls reasoning from AI response using substring matching
- **Step Output**: Displays reasoning in the UI for transparency

#### **Reasoning Types Generated**:

1. **Tool Usage Reasoning**: Explains why specific tools were selected and used
2. **No-Tool Reasoning**: Explains why tools weren't needed (relying on training data)
3. **Follow-up Reasoning**: Explains reuse of previous tool data
4. **FX Data Reasoning**: Explains FX transaction data retrieval and processing

The system ensures **100% transparency** by requiring reasoning for every response and displaying it prominently in the step output.