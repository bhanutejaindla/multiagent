from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv
from .rag import query_documents
import asyncio

# Direct imports from MCP server files (Python functions)
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp_servers.research.server import web_search
from mcp_servers.compliance.server import redact_pii
from mcp_servers.citation_validation.server import verify_citations_internal, parse_web_search_results
from .kafka_client import KafkaProducerClient, TOPIC_NAME
from .report_generator import ReportGenerator
from datetime import datetime
from typing import Optional

load_dotenv()

# Initialize LLM
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("WARNING: OPENAI_API_KEY not found. Using mock LLM response.")
    llm = None
else:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

async def send_event(job_id: Optional[int], status: str, progress: float):
    if job_id:
        producer = KafkaProducerClient()
        await producer.start()
        try:
            event = {
                "job_id": job_id,
                "status": "running", # Keep overall status as running
                "progress": progress,
                "timestamp": datetime.utcnow().isoformat(),
                "details": status # Add specific stage as details if needed, or map to status
            }
            # If status is completed, update overall status
            if status == "completed":
                event["status"] = "completed"
                
            await producer.send_message(TOPIC_NAME, event)
        except Exception as e:
            print(f"Failed to send event: {e}")
        finally:
            await producer.stop()

async def run_agent(query: str, job_id: Optional[int] = None, generate_report: bool = True):
    """Enhanced Agent Pipeline with Citation Verification"""
    print(f"--- Starting Agent for Query: {query} ---")
    
    # Bypass LLM logic if API key is missing
    if llm is None:
        print("Using mock answer due to missing API Key.")
        await asyncio.sleep(2) # Simulate work
        final_answer = "The current Chief Minister of Telangana is Revanth Reddy. He assumed office on December 7, 2013. [1]"
        
        # Simulate events
        await send_event(job_id, "drafting", 0.55)
        await send_event(job_id, "verifying", 0.7)
        await send_event(job_id, "refining", 0.85)
        await send_event(job_id, "completed", 1.0)
        
        # Generate Reports
        print("7. Generating Reports...")
        report_paths = {}
        if generate_report:
            try:
                generator = ReportGenerator()
                filename = f"report_{job_id}" if job_id else f"report_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                
                docx_path = await asyncio.to_thread(generator.generate_docx, final_answer, filename)
                pdf_path = await asyncio.to_thread(generator.generate_pdf, final_answer, filename)
                
                report_paths = {
                    "docx": docx_path,
                    "pdf": pdf_path
                }
                print(f"Reports generated: {report_paths}")
            except Exception as e:
                print(f"Report generation failed: {e}")
        else:
            print("Skipping report generation as requested.")

        print("\n--- Agent Finished ---")
        return {
            "answer": final_answer,
            "reports": report_paths
        }

    # 1. Retrieve Context
    print("1. Retrieving Context...")
    await send_event(job_id, "retrieving_context", 0.2)
    context = await asyncio.to_thread(query_documents, query)
    
    # 2. Web Research
    print("2. Performing Web Research...")
    await send_event(job_id, "web_research", 0.35)
    web_results = ""
    try:
        web_results = await asyncio.to_thread(web_search, query, max_results=5)
        print(f"✓ Found {len(web_results.split('\\n\\n'))} web results")
    except Exception as e:
        web_results = f"Search failed: {e}"

    # 3. Synthesize Answer
    print("3. Synthesizing Answer...")
    await send_event(job_id, "drafting", 0.55)
    synthesis_prompt = ChatPromptTemplate.from_template(
        """You are a research analyst. Answer the query using the provided sources.

Query: {query}

Web Search Results (USE THESE for current information):
{web_results}

Internal Documents:
{context}

IMPORTANT INSTRUCTIONS:
- Prioritize web search results for current/recent information
- Cite sources using [1], [2], etc. matching the numbered sources above
- Every factual claim MUST have a citation
- Example: "The current CM is Revanth Reddy [1]"

Answer with citations:"""
    )
    chain = synthesis_prompt | llm
    draft_answer = await chain.ainvoke({
        "query": query,
        "context": context,
        "web_results": web_results
    })
    draft_answer = draft_answer.content
    print(f"Draft: {draft_answer[:100]}...")
    
    # 4. Verify Citations
    print("4. Verifying Citations...")
    await send_event(job_id, "verifying", 0.7)
    
    # Parse web results into structured sources
    sources = await asyncio.to_thread(parse_web_search_results, web_results)
    
    # Add context as additional source
    if context:
        sources.append({
            'id': 'internal',
            'title': 'Internal Documents',
            'text': context,
            'url': 'internal'
        })
    
    # Run verification
    verification = await asyncio.to_thread(
        verify_citations_internal,
        draft_answer,
        sources,
        strict_mode=False
    )
    
    print(f"\n{verification['summary']}")
    print(f"Score: {verification['score']} ({verification['supported_claims']}/{verification['total_claims']} claims supported)")
    
    if verification['issues']:
        print(f"\n⚠️ Found {len(verification['issues'])} issues:")
        for issue in verification['issues'][:3]:  # Show first 3
            print(f"  {issue}")
    
    # 5. Refine Answer if needed
    final_answer = draft_answer
    
    if not verification['is_valid'] or verification['score'] < 0.8:
        print("\n5. Refining Answer...")
        await send_event(job_id, "refining", 0.85)
        
        refine_prompt = ChatPromptTemplate.from_template(
            """Fix the citation issues in this answer.

ORIGINAL QUERY: {query}

ORIGINAL ANSWER: 
{draft_answer}

VERIFICATION ISSUES:
{issues}

SOURCES AVAILABLE:
{web_results}

INSTRUCTIONS:
- Fix all issues mentioned above
- Ensure EVERY factual claim has a citation [1], [2], etc.
- Use ONLY information from the sources provided
- For current information (like "current CM"), use the web search results
- Do not introduce information from your training data

Corrected Answer:"""
        )
        chain = refine_prompt | llm
        refined = await chain.ainvoke({
            "query": query,
            "draft_answer": draft_answer,
            "issues": "\n".join(verification['issues']),
            "web_results": web_results
        })
        final_answer = refined.content
        print(f"Refined: {final_answer[:100]}...")
        
        # Verify again
        verification2 = await asyncio.to_thread(
            verify_citations_internal,
            final_answer,
            sources,
            strict_mode=False
        )
        print(f"\nRe-verification: {verification2['summary']}")
    else:
        print("\n5. ✅ No refinement needed")
    
    # 6. Compliance Check
    print("\n6. Checking Compliance...")
    try:
        final_answer = await asyncio.to_thread(redact_pii, final_answer)
    except Exception as e:
        print(f"Compliance check failed: {e}")
        
    # 7. Generate Reports
    print("7. Generating Reports...")
    report_paths = {}
    if generate_report:
        try:
            generator = ReportGenerator()
            filename = f"report_{job_id}" if job_id else f"report_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            docx_path = await asyncio.to_thread(generator.generate_docx, final_answer, filename)
            pdf_path = await asyncio.to_thread(generator.generate_pdf, final_answer, filename)
            
            report_paths = {
                "docx": docx_path,
                "pdf": pdf_path
            }
            print(f"Reports generated: {report_paths}")
        except Exception as e:
            print(f"Report generation failed: {e}")
    else:
        print("Skipping report generation as requested.")

    print("\n--- Agent Finished ---")
    await send_event(job_id, "completed", 1.0)
    
    return {
        "answer": final_answer,
        "reports": report_paths
    }
