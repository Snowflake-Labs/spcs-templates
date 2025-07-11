import logging
import os
import sys
import gradio as gr
import requests
from fastapi import FastAPI, Request

SERVICE_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVICE_PORT = os.getenv('SERVER_PORT', 8080)
SNOWFLAKE_HOST = os.getenv("SNOWFLAKE_HOST")

SEMANTIC_MODEL_PATH = "@cortex_analyst_demo.revenue_timeseries.raw_data/revenue_timeseries.yaml"
API_TIMEOUT = 60  # in seconds

def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            '%(name)s [%(asctime)s] [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    return logger

logger = get_logger('chatbot')

app = FastAPI()

@app.middleware("http")
async def get_ingress_user_token(request: Request, call_next):
    """Capture the current user token from ingress"""
    global ingress_user_token
    ingress_user_token = request.headers.get('Sf-Context-Current-User-Token')
    response = await call_next(request)
    return response

def get_login_token():
    with open("/snowflake/session/token", "r") as f:
        return f.read()

def get_request_headers():
    return {
        "Authorization": f"Bearer {get_login_token()}.{ingress_user_token}",
        "X-Snowflake-Authorization-Token-Type": "OAUTH",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

analyst_history = None

def clear_state():
    global analyst_history
    analyst_history = []

clear_state()
    
def send_sql(sql_query):
    """Executes a SQL query using Snowflake's REST API."""
    logger.debug(f"Executing SQL query: {sql_query}")
    
    request_body = {
        "statement": sql_query,
    }
    
    url = f"https://{SNOWFLAKE_HOST}/api/v2/statements"
    
    try:
        resp = requests.post(url=url, json=request_body, headers=get_request_headers(), timeout=API_TIMEOUT)
        
        if resp.status_code >= 400:
            raise gr.Error(f"SQL Error: HTTP {resp.status_code} - {resp.text}")
        
        response_data = resp.json()
        logger.debug(f"SQL Response data: {response_data}")
        
        # Format the SQL result for display
        if "resultSetMetaData" in response_data and "rowType" in response_data["resultSetMetaData"]:
            # Get column names
            columns = [col["name"] for col in response_data["resultSetMetaData"].get("rowType", [])]
            rows = response_data["data"]
            
            # Format as a table
            result ="| " + " | ".join(columns) + " |\n"
            result +=  "| " + " | ".join(["---" for _ in columns]) + " |\n"
            for row in rows:
                result +="| " +  " | ".join(str(cell) for cell in row) + " |\n"
                
            return result

        return "SQL query executed successfully but returned no data."
        
    except Exception as e:
        raise gr.Error(f"SQL Error: {str(e)}")

       
async def send_message(message, history):
    logger.debug(f"Received message: {message}");
    analyst_history.append({
        "role": "user", 
        "content": [
        {
                "type": "text",
                "text": message
            }
        ]
    })
    request_body = {
        "messages": analyst_history,
        "semantic_model_file": SEMANTIC_MODEL_PATH
    }

    url = f"https://{SNOWFLAKE_HOST}/api/v2/cortex/analyst/message"
    
    try:
        resp = requests.post(url=url, json=request_body, headers=get_request_headers(), timeout=API_TIMEOUT)
        
        if resp.status_code >= 400:
            raise gr.Error(f"HTTP Error: {resp.status_code} - {resp.text}")
            
        response_data = resp.json()
        logger.debug(f"Response data: {response_data}")

        # Process the response message content
        response_messages = []
        yield response_messages
        
        # Extract text content from the message
        if "message" in response_data and "content" in response_data["message"]:
            analyst_history.append(response_data["message"])
            logger.debug(f"History: {analyst_history}")

            for content_item in response_data["message"]["content"]:
                if content_item.get("type") == "text":
                    response_messages.append(
                        gr.ChatMessage(
                            content = content_item.get("text")
                        )
                    )
                elif content_item.get("type") == "sql":
                    statement = content_item.get('statement')
                    m = gr.ChatMessage(
                            content = f"Executing the following SQL query:\n```sql\n{statement}\n```",
                            metadata={"title": "Running SQL", "status": "pending"}
                        )
                    response_messages.append(m)
                    yield response_messages
                    sql_result = send_sql(statement);
                    m.metadata["status"] = "done"
                    response_messages.append(
                        gr.ChatMessage(
                            content=f"Response data:\n{sql_result}"
                        )
                    )
                elif content_item.get("type") == "suggestions":
                    m = gr.ChatMessage(
                            content= "",
                            options = []
                        )
                    for suggestion_index, suggestion in enumerate(content_item["suggestions"]):
                        m.options.append({
                            "value": suggestion
                        })
                    response_messages.append(m)
                else:
                    pass
                yield response_messages

        # Add warnings if they exist
        if "warnings" in response_data and response_data["warnings"]:
            for warning in response_data["warnings"]:
                gr.Warning(warning.get('message', ''))
            
        # If no content was found, return a default message
        if len(response_messages) == 0:
            response_messages.append(
                gr.ChatMessage(content =  "No response text received")
            )
        
    except Exception as e:
        err = f"Unexpected error: {e}"
        logger.error(err)
        clear_state()
        raise gr.Error(err)
    
    logger.debug(f"Response messages: {response_messages}")
    yield response_messages

@app.get("/healthcheck")
async def readiness_probe():
    return "I'm ready"

# Build chatbot
with gr.Blocks() as bot:
    chatbot = gr.Chatbot(type="messages")
    chatbot.clear(clear_state) 
    gr.ChatInterface(
        send_message, 
        type="messages",
        examples=["What questions can I ask?"],
        title="Cortex Analyst",
        chatbot=chatbot
    )


# Mount the Gradio app to FastAPI
gr.mount_gradio_app(app, bot, path="")

# Start the app 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=int(SERVICE_PORT))
    logger.debug(f"Chatbot app running on {SERVICE_HOST}:{SERVICE_PORT}")
