# Setting up Google BigQuery for DataChat

DataChat can be extended to query Google BigQuery datasets. This guide details the prerequisites and configuration steps required to set up your environment.

## Prerequisites

1.  **Google Cloud Platform (GCP) Account**: You need an active GCP account.
2.  **Project**: A GCP project with BigQuery enabled.
3.  **Service Account**: A service account with appropriate permissions.

## Step-by-Step Setup

### 1. Create a Google Cloud Project

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Click on the project dropdown at the top and select **New Project**.
3.  Enter a project name and click **Create**.
4.  Once created, select the project.

### 2. Enable BigQuery API

1.  In the left sidebar, navigate to **APIs & Services** > **Library**.
2.  Search for **BigQuery API**.
3.  Click **Enable** if it's not already enabled.

### 3. Create a Service Account

1.  Navigate to **IAM & Admin** > **Service Accounts**.
2.  Click **+ Create Service Account**.
3.  Enter a name (e.g., `datachat-bigquery`) and description. Click **Create and Continue**.
4.  **Grant Access**:
    *   Select the role **BigQuery Data Viewer** (to allow reading data).
    *   Select **BigQuery Job User** (to allow running queries).
    *   Click **Continue** and then **Done**.

### 4. Generate & Download Key

1.  Click on the newly created service account email.
2.  Go to the **Keys** tab.
3.  Click **Add Key** > **Create new key**.
4.  Select **JSON** and click **Create**.
5.  A `.json` file will be downloaded to your computer.
6.  **Secure this file!** Move it to a secure location in your project (e.g., `secrets/bigquery-key.json`).
    *   *Note: Ensure this file is added to `.gitignore`.*

### 5. Install Dependencies

You will need the BigQuery SQLAlchemy dialect:

```bash
pip install sqlalchemy-bigquery google-cloud-bigquery
```

### 6. Configuration

Update your `.env` file to configure DataChat for BigQuery.

> **Note**: While the current version of DataChat natively supports internal SQLite, PostgreSQL, and MySQL via factory, BigQuery support can be added by extending the `ConnectorFactory`.

**Example `.env` configuration:**

```env
DB_TYPE=bigquery
DB_PROJECT_ID=your-project-id
DB_DATASET=your-dataset-name
GOOGLE_APPLICATION_CREDENTIALS=secrets/bigquery-key.json
```

### 7. Integrating with DataChat Code (Extension)

To fully enable BigQuery, you would extend `src/connectors/factory.py` to handle the `bigquery` type:

```python
# In src/connectors/factory.py

elif db_type == 'bigquery':
    project = os.getenv('DB_PROJECT_ID')
    dataset = os.getenv('DB_DATASET')
    key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    # SQLAlchemy connection string for BigQuery
    # bigquery://project-id/dataset_id
    config = {
        'connection_string': f'bigquery://{project}/{dataset}',
        'credentials_path': key_path
    }
    return BigQueryConnector(config)
```

And verify your `src/connectors/base.py` or specific BigQuery connector implementation handles the SQLAlchemy engine creation using these credentials.
