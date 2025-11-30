# Spec2Sim-Agent Cloud Deployment

This directory contains all files required to deploy Spec2Sim-Agent to **Vertex AI Agent Engine**.

## 📋 Prerequisites

1.  **Google Cloud Account** ($300 free credit for new users)
2.  **Google Cloud Project** (Billing enabled)
3.  **ADK CLI**: `pip install google-adk`
4.  **Google Cloud CLI**: [Installation Guide](https://cloud.google.com/sdk/docs/install)

## 📁 File Description

-   `agent.py` - Agent deployment entry point
-   `requirements.txt` - Python dependencies
-   `.env` - Environment variable configuration
-   `.agent_engine_config.json` - Agent Engine resource configuration
-   `DEPLOYMENT_GUIDE.md` - Complete deployment guide (detailed instructions)

## 🚀 Quick Start

### 1. Prepare Files

Run from the project root directory (Windows PowerShell):

```powershell
# Copy core code to deployment directory
xcopy core deployment\core\ /E /I /Y
xcopy agents deployment\agents\ /E /I /Y
xcopy servers deployment\servers\ /E /I /Y
```

### 2. Configure GCP Authentication

```powershell
# Login to Google Cloud
gcloud auth login

# Set application default credentials
gcloud auth application-default login

# Set Project ID (Replace with your Project ID)
$PROJECT_ID = "YOUR_PROJECT_ID"
gcloud config set project $PROJECT_ID
```

### 3. Update Configuration

Edit the `.env` file and set your Project ID:

```bash
GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
```

> **⚠️ Security Warning**: The `.env` file may contain sensitive information. Ensure it is not committed to version control (already excluded in `.gitignore`).

### 4. Enable APIs

Click the link to enable all required APIs:
https://console.cloud.google.com/flows/enableapi?apiid=aiplatform.googleapis.com,storage.googleapis.com,logging.googleapis.com,monitoring.googleapis.com,cloudtrace.googleapis.com,telemetry.googleapis.com

### 5. Deploy

```powershell
# Set deployment parameters
$PROJECT_ID = "YOUR_PROJECT_ID"
$REGION = "us-west1"  # Optional: us-east4, europe-west1, europe-west4

# Execute deployment
adk deploy agent_engine `
  --project=$PROJECT_ID `
  --region=$REGION `
  deployment `
  --agent_engine_config_file=deployment/.agent_engine_config.json
```

⏱️ Deployment takes 3-5 minutes

### 6. Test

Test using Python SDK:

```python
import vertexai
from vertexai import agent_engines

PROJECT_ID = "YOUR_PROJECT_ID"
REGION = "us-west1"
vertexai.init(project=PROJECT_ID, location=REGION)

# Get deployed agent
agents_list = list(agent_engines.list())
remote_agent = agents_list[0]

# Test query
spec = """
Traffic Light: Red, Yellow, Green
Red -> Green (30s), Green -> Yellow (20s), Yellow -> Red (3s)
"""

async for item in remote_agent.async_stream_query(
    message=f"Process: {spec}",
    user_id="test_user",
):
    print(item)
```

### 7. Clean Up Resources

**Important**: Delete resources after testing to avoid charges!

```python
agent_engines.delete(resource_name=remote_agent.resource_name, force=True)
```

## 💰 Cost Information

-   Agent Engine has a [monthly free tier](https://docs.cloud.google.com/agent-builder/agent-engine/overview#pricing)
-   This deployment configuration (0-1 instance, 2CPU/4GB) falls within the free tier
-   **However, please ensure to delete resources after testing!**

## 📚 More Information

For detailed instructions, please check:
-   Complete Deployment Document: `implementation_plan.md` (in artifacts directory)
-   [ADK Official Documentation](https://google.github.io/adk-docs/)
-   [Agent Engine Documentation](https://docs.cloud.google.com/agent-builder/agent-engine/overview)