#!/usr/bin/env python3
"""
Test script for reasoning visualization
This script demonstrates the reasoning process without requiring Chainlit
"""

import asyncio
import time
from typing import List, Dict, Any

class ReasoningTracker:
    """Tracks reasoning steps and tool usage"""
    
    def __init__(self):
        self.reasoning_steps = []
        self.tool_results = []
        self.start_time = time.time()
    
    def add_step(self, step_type: str, content: str, **kwargs):
        """Add a reasoning step"""
        step = {
            "step_type": step_type,
            "content": content,
            "timestamp": time.time() - self.start_time,
            **kwargs
        }
        self.reasoning_steps.append(step)
        print(f"🧠 [{step_type.upper()}] {content}")
    
    def add_tool_result(self, tool_name: str, input_data: Any, result: Any):
        """Add a tool result"""
        tool_result = {
            "tool_name": tool_name,
            "input": input_data,
            "result": result,
            "timestamp": time.time() - self.start_time
        }
        self.tool_results.append(tool_result)
        print(f"🔧 [TOOL] {tool_name}: {str(result)[:100]}...")

class MockReasoningAgent:
    """Mock agent that simulates reasoning process"""
    
    def __init__(self):
        self.tracker = ReasoningTracker()
    
    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process a user message with full reasoning tracking"""
        self.tracker = ReasoningTracker()  # Reset for new message
        
        # Step 1: Initial analysis
        self.tracker.add_step("analysis", f"Analyzing user request: {user_message}")
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Step 2: Determine if tools are needed
        needs_tools = await self._analyze_tool_need(user_message)
        
        if needs_tools:
            # Step 3: Execute with tools
            result = await self._execute_with_tools(user_message)
        else:
            # Step 3: Direct response
            result = await self._execute_direct_response(user_message)
        
        # Step 4: Final reasoning
        self.tracker.add_step("completion", "Response generation completed")
        
        return {
            "response": result,
            "reasoning_steps": self.tracker.reasoning_steps,
            "tool_results": self.tracker.tool_results
        }
    
    async def _analyze_tool_need(self, user_message: str) -> bool:
        """Analyze if tools are needed"""
        tool_keywords = [
            "search", "find", "get", "retrieve", "fetch", "query", "data",
            "transaction", "exchange", "foreign", "currency", "file", "document",
            "lookup", "check", "verify", "calculate", "compute"
        ]
        
        message_lower = user_message.lower()
        needs_tools = any(keyword in message_lower for keyword in tool_keywords)
        
        self.tracker.add_step(
            "tool_analysis", 
            f"Tool need analysis: {'Tools needed' if needs_tools else 'No tools needed'}"
        )
        await asyncio.sleep(0.05)  # Simulate analysis time
        
        return needs_tools
    
    async def _execute_with_tools(self, user_message: str) -> str:
        """Execute with tool usage"""
        self.tracker.add_step("tool_execution", "Starting tool-based execution")
        
        # Simulate tool selection
        available_tools = ["GetForeignExchangeTransactionData", "SearchDocuments", "CalculateExchangeRate"]
        self.tracker.add_step("tool_selection", f"Available tools: {available_tools}")
        await asyncio.sleep(0.1)
        
        # Simulate tool usage
        if "transaction" in user_message.lower() or "exchange" in user_message.lower():
            tool_name = "GetForeignExchangeTransactionData"
            tool_input = {"limit": 10, "currency": "USD"}
            tool_output = {
                "transactions": [
                    {"id": "1", "amount": 1000, "currency": "USD", "date": "2024-01-15"},
                    {"id": "2", "amount": 2000, "currency": "EUR", "date": "2024-01-14"}
                ]
            }
            
            self.tracker.add_tool_result(tool_name, tool_input, tool_output)
            self.tracker.add_step("tool_used", f"Successfully used tool '{tool_name}'")
            await asyncio.sleep(0.5)  # Simulate tool execution time
            
            return f"Found {len(tool_output['transactions'])} foreign exchange transactions. The latest transaction is for {tool_output['transactions'][0]['amount']} {tool_output['transactions'][0]['currency']}."
        
        elif "search" in user_message.lower() or "find" in user_message.lower():
            tool_name = "SearchDocuments"
            tool_input = {"query": user_message}
            tool_output = {"results": ["Document 1", "Document 2", "Document 3"]}
            
            self.tracker.add_tool_result(tool_name, tool_input, tool_output)
            self.tracker.add_step("tool_used", f"Successfully used tool '{tool_name}'")
            await asyncio.sleep(0.3)
            
            return f"Found {len(tool_output['results'])} documents matching your search."
        
        else:
            return "Tool execution completed but no specific tool matched the request."
    
    async def _execute_direct_response(self, user_message: str) -> str:
        """Execute direct response without tools"""
        self.tracker.add_step("direct_response", "Generating direct response without tools")
        await asyncio.sleep(0.2)  # Simulate response generation time
        
        self.tracker.add_step("response_generation", "Direct response generated successfully")
        
        return f"Based on my knowledge, here's what I can tell you about: {user_message}"

def display_reasoning_visualization(reasoning_steps: List[Dict], tool_results: List[Dict]):
    """Display reasoning process in a visually appealing way"""
    if not reasoning_steps:
        print("No reasoning steps to display")
        return
    
    print("\n" + "="*60)
    print("🧠 AGENT REASONING TIMELINE")
    print("="*60)
    
    for i, step in enumerate(reasoning_steps, 1):
        step_type = step.get("step_type", "unknown")
        content = step.get("content", "")
        timestamp = step.get("timestamp", 0)
        
        # Choose emoji based on step type
        emoji_map = {
            "analysis": "🔍",
            "tool_analysis": "🤔",
            "tool_execution": "⚙️",
            "tool_selection": "📋",
            "tool_used": "✅",
            "direct_response": "💭",
            "response_generation": "✨",
            "completion": "🎯",
            "error": "❌"
        }
        
        emoji = emoji_map.get(step_type, "📝")
        
        print(f"\n{emoji} Step {i} ({step_type.replace('_', ' ').title()}):")
        print(f"   ⏱️  Time: {timestamp:.2f}s")
        print(f"   📝 {content}")
    
    # Add tool results summary
    if tool_results:
        print(f"\n{'='*60}")
        print("🔧 TOOL EXECUTION SUMMARY")
        print("="*60)
        
        for result in tool_results:
            tool_name = result.get("tool_name", "Unknown")
            result_content = str(result.get("result", ""))
            timestamp = result.get("timestamp", 0)
            
            print(f"\n🔧 Tool: {tool_name}")
            print(f"   ⏱️  Time: {timestamp:.2f}s")
            print(f"   📊 Result: {result_content[:100]}...")
    
    print("\n" + "="*60)

async def test_reasoning_agent():
    """Test the reasoning agent with different types of queries"""
    
    agent = MockReasoningAgent()
    
    # Test queries
    test_queries = [
        "Get me the latest foreign exchange transactions",
        "What is the capital of France?",
        "Search for documents about machine learning",
        "Calculate the exchange rate between USD and EUR",
        "Tell me a joke"
    ]
    
    print("🧠 REASONING AGENT DEMONSTRATION")
    print("="*60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {query}")
        print("="*60)
        
        # Process the query
        result = await agent.process_message(query)
        
        # Display reasoning visualization
        display_reasoning_visualization(
            result["reasoning_steps"], 
            result["tool_results"]
        )
        
        # Show final response
        print(f"\n💬 FINAL RESPONSE:")
        print(f"   {result['response']}")
        
        # Wait between tests
        if i < len(test_queries):
            print("\n" + "⏳ Waiting 2 seconds before next test...")
            await asyncio.sleep(2)

if __name__ == "__main__":
    print("Starting Reasoning Agent Test...")
    asyncio.run(test_reasoning_agent())
    print("\n✅ Test completed!") 