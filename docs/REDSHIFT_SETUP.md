# Setting up AWS Redshift for DataChat

DataChat can be extended to query AWS Redshift clusters. This guide details the prerequisites and configuration steps required to set up your environment.

## Prerequisites

1.  **AWS Account**: You need an active AWS account.
2.  **Redshift Cluster**: A provisioned Redshift cluster or Serverless endpoint.
3.  **Network Access**: Ensure your cluster's Security Group allows inbound traffic from your application's IP (port 5439 by default).
4.  **Database Credentials**: Username and password with read access to the target schemas/tables.

## Step-by-Step Setup

### 1. Create/Access a Redshift Cluster

1.  Go to the [AWS Management Console](https://console.aws.amazon.com/redshift/).
2.  Navigate to **Clusters** and create a new cluster if you don't have one.
3.  Note down the **Endpoint** (e.g., `your-cluster. region.redshift.amazonaws.com`), **Port**, **Database Name**, and **Master Username**.

### 2. Configure Security Group

1.  In the Redshift console, click on your cluster.
2.  In the **Properties** tab, find the **Network and security** section.
3.  Click on the VPC Security Group.
4.  Add an **Inbound Rule**:
    *   **Type**: Redshift (TCP)
    *   **Port Range**: 5439
    *   **Source**: My IP (for local dev) or your application server's security group/IP range.

### 3. Install Dependencies

You need the `sqlalchemy-redshift` dialect and `psycopg2-binary` driver (already included in `requirements.txt`):

```bash
pip install sqlalchemy-redshift psycopg2-binary
```

### 4. Configuration

DataChat uses `config/sources.yaml` to manage data sources. You should configure Redshift there using environment variables for credentials.

**1. Update `.env` file:**

Add your Redshift credentials to the `.env` file (do not commit this):

```env
REDSHIFT_HOST=your-cluster-endpoint.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DB=dev
REDSHIFT_USER=your_username
REDSHIFT_PASSWORD=your_password
REDSHIFT_SCHEMA=public
```

**2. Update `config/sources.yaml`:**

Ensure you have a Redshift source defined in your sources configuration:

```yaml
marketing_redshift:
  type: redshift
  description: "Marketing campaign analytics from Redshift"
  config:
    host: "${REDSHIFT_HOST}"
    port: ${REDSHIFT_PORT}
    database: "${REDSHIFT_DB}"
    username: "${REDSHIFT_USER}"
    password: "${REDSHIFT_PASSWORD}"
    schema: "${REDSHIFT_SCHEMA}"
```

### 5. Activate the Source

To use Redshift, set the `ACTIVE_SOURCE` environment variable:

```bash
export ACTIVE_SOURCE=marketing_redshift
```

Or in your `.env`:

```env
ACTIVE_SOURCE=marketing_redshift
```

### 6. Verification

Run the application and check the logs to verify the connection:

```bash
python -m src.api.main
```

You should see logs indicating initialization of the `RedshiftConnector`.
