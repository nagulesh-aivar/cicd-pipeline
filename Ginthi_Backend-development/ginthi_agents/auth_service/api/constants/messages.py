class ClientAPIKeyMessages:
    """Messages for Client API Key operations"""

    # --- Success Messages ---
    CREATED_SUCCESS = "Client API Key created successfully: {id}"
    RETRIEVED_SUCCESS = "Client API Key retrieved: {id}"
    RETRIEVED_ALL_SUCCESS = "Retrieved {count} Client API Keys"
    UPDATED_SUCCESS = "Client API Key updated successfully: {id}"
    DELETED_SUCCESS = "Client API Key deleted successfully: {id}"

    # --- Error Messages ---
    NOT_FOUND = "Client API Key with ID {id} not found"
    CREATE_ERROR = "Error creating Client API Key: {error}"
    RETRIEVE_ERROR = "Error retrieving Client API Key: {error}"
    RETRIEVE_ALL_ERROR = "Error retrieving Client API Keys: {error}"
    UPDATE_ERROR = "Error updating Client API Key: {error}"
    DELETE_ERROR = "Error deleting Client API Key: {error}"
    INTERNAL_SERVER_ERROR = "An internal server error occurred"
    VALIDATION_ERROR = "Validation error: {error}"

class ClientMessages:
    """Messages for Client operations"""

    # Success messages
    CREATED_SUCCESS = "Client created successfully: {name}"
    RETRIEVED_SUCCESS = "Client retrieved: {name}"
    RETRIEVED_ALL_SUCCESS = "Retrieved {count} clients"
    UPDATED_SUCCESS = "Client updated: {name}"
    DELETED_SUCCESS = "Client {id} deleted successfully"

    # Error messages
    NOT_FOUND = "Client with ID {id} not found"
    DUPLICATE_NAME = "Client with name '{name}' already exists"
    CREATE_ERROR = "Error creating client: {error}"
    RETRIEVE_ERROR = "Error retrieving client: {error}"
    RETRIEVE_ALL_ERROR = "Error retrieving clients: {error}"
    UPDATE_ERROR = "Error updating client: {error}"
    DELETE_ERROR = "Error deleting client: {error}"
    INTERNAL_SERVER_ERROR = "An internal server error occurred"
    VALIDATION_ERROR = "Validation error: {error}"

class LeadAdminMessages:
    """Messages for Lead Admin operations"""

    # Success messages
    CREATED_SUCCESS = "Lead Admin created successfully: {email}"
    RETRIEVED_SUCCESS = "Lead Admin retrieved: {email}"
    RETRIEVED_ALL_SUCCESS = "Retrieved {count} Lead Admins"
    UPDATED_SUCCESS = "Lead Admin updated: {email}"
    DELETED_SUCCESS = "Lead Admin {id} deleted successfully"

    # Error messages
    NOT_FOUND = "Lead Admin with ID {id} not found"
    DUPLICATE_EMAIL = "Lead Admin with email '{email}' already exists"
    CREATE_ERROR = "Error creating Lead Admin: {error}"
    RETRIEVE_ERROR = "Error retrieving Lead Admin: {error}"
    RETRIEVE_ALL_ERROR = "Error retrieving Lead Admins: {error}"
    UPDATE_ERROR = "Error updating Lead Admin: {error}"
    DELETE_ERROR = "Error deleting Lead Admin: {error}"
    INTERNAL_SERVER_ERROR = "An internal server error occurred"
    VALIDATION_ERROR = "Validation error: {error}"

class ClientServerMessages:
    """Messages for Client Server operations"""

    # Success messages
    CREATED_SUCCESS = "Client Server created successfully: {name}"
    RETRIEVED_SUCCESS = "Client Server retrieved: {name}"
    RETRIEVED_ALL_SUCCESS = "Retrieved {count} Client Servers"
    UPDATED_SUCCESS = "Client Server updated: {name}"
    DELETED_SUCCESS = "Client Server {id} deleted successfully"

    # Error messages
    NOT_FOUND = "Client Server with ID {id} not found"
    DUPLICATE_NAME = "Client Server with name '{name}' already exists"
    CREATE_ERROR = "Error creating Client Server: {error}"
    RETRIEVE_ERROR = "Error retrieving Client Server: {error}"
    RETRIEVE_ALL_ERROR = "Error retrieving Client Servers: {error}"
    UPDATE_ERROR = "Error updating Client Server: {error}"
    DELETE_ERROR = "Error deleting Client Server: {error}"
    INTERNAL_SERVER_ERROR = "An internal server error occurred"
    VALIDATION_ERROR = "Validation error: {error}"
    
class CreditEntryMessages:
    """Messages for AI Credit Entry operations"""

    # Success messages
    CREATED_SUCCESS = "Credit entry created successfully: {id}"
    RETRIEVED_SUCCESS = "Credit entry retrieved: {id}"
    RETRIEVED_ALL_SUCCESS = "Retrieved {count} credit entries"
    UPDATED_SUCCESS = "Credit entry updated successfully: {id}"
    DELETED_SUCCESS = "Credit entry deleted successfully: {id}"

    # Error messages
    NOT_FOUND = "Credit entry with ID {id} not found"
    CREATE_ERROR = "Error creating credit entry: {error}"
    RETRIEVE_ERROR = "Error retrieving credit entry: {error}"
    RETRIEVE_ALL_ERROR = "Error retrieving credit entries: {error}"
    UPDATE_ERROR = "Error updating credit entry: {error}"
    DELETE_ERROR = "Error deleting credit entry: {error}"
    INTERNAL_SERVER_ERROR = "An internal server error occurred"
    VALIDATION_ERROR = "Validation error: {error}"

class CreditLedgerMessages:
    """Messages for AI Credit Ledger operations"""

    # Success messages
    CREATED_SUCCESS = "Credit ledger created successfully for client: {client_id}"
    RETRIEVED_SUCCESS = "Credit ledger retrieved for client: {client_id}"
    UPDATED_SUCCESS = "Credit ledger updated successfully for client: {client_id}"
    DELETED_SUCCESS = "Credit ledger deleted successfully for client: {client_id}"

    # Error messages
    NOT_FOUND = "Credit ledger for client ID {client_id} not found"
    CREATE_ERROR = "Error creating credit ledger: {error}"
    RETRIEVE_ERROR = "Error retrieving credit ledger: {error}"
    UPDATE_ERROR = "Error updating credit ledger: {error}"
    INTERNAL_SERVER_ERROR = "An internal server error occurred"
    DELETE_ERROR = "Error deleting credit ledger: {error}"
    VALIDATION_ERROR = "Validation error: {error}"

class FeedbackMessages:
    """Messages for Feedback operations"""

    # Success messages
    CREATED_SUCCESS = "Feedback submitted successfully: {id}"
    RETRIEVED_SUCCESS = "Feedback retrieved: {id}"
    RETRIEVED_ALL_SUCCESS = "Retrieved {count} feedback entries"
    UPDATED_SUCCESS = "Feedback updated successfully: {id}"
    DELETED_SUCCESS = "Feedback deleted successfully: {id}"

    # Error messages
    NOT_FOUND = "Feedback with ID {id} not found"
    CREATE_ERROR = "Error submitting feedback: {error}"
    RETRIEVE_ERROR = "Error retrieving feedback: {error}"
    RETRIEVE_ALL_ERROR = "Error retrieving feedback entries: {error}"
    UPDATE_ERROR = "Error updating feedback: {error}"
    DELETE_ERROR = "Error deleting feedback: {error}"
    INTERNAL_SERVER_ERROR = "An internal server error occurred"
    VALIDATION_ERROR = "Validation error: {error}"

class WorkflowMessages:   
    """Messages for Workflow operations"""

    # Success messages
    CREATED_SUCCESS = "Workflow created successfully: {id}"
    RETRIEVED_SUCCESS = "Workflow retrieved: {id}"
    RETRIEVED_ALL_SUCCESS = "Retrieved {count} workflows"
    UPDATED_SUCCESS = "Workflow updated successfully: {id}"
    DELETED_SUCCESS = "Workflow deleted successfully: {id}"

    # Error messages
    NOT_FOUND = "Workflow with ID {id} not found"
    CREATE_ERROR = "Error creating workflow: {error}"
    RETRIEVE_ERROR = "Error retrieving workflow: {error}"
    RETRIEVE_ALL_ERROR = "Error retrieving workflows: {error}"
    UPDATE_ERROR = "Error updating workflow: {error}"
    DELETE_ERROR = "Error deleting workflow: {error}"
    INTERNAL_SERVER_ERROR = "An internal server error occurred"
    VALIDATION_ERROR = "Validation error: {error}"

class WorkflowExecutionMessages:    
    """Messages for Workflow Execution operations"""

    # Success messages
    CREATED_SUCCESS = "Workflow execution created successfully: {id}"
    RETRIEVED_SUCCESS = "Workflow execution retrieved: {id}"
    RETRIEVED_ALL_SUCCESS = "Retrieved {count} workflow executions"
    UPDATED_SUCCESS = "Workflow execution updated successfully: {id}"
    DELETED_SUCCESS = "Workflow execution deleted successfully: {id}"

    # Error messages
    NOT_FOUND = "Workflow execution with ID {id} not found"
    CREATE_ERROR = "Error creating workflow execution: {error}"
    RETRIEVE_ERROR = "Error retrieving workflow execution: {error}"
    RETRIEVE_ALL_ERROR = "Error retrieving workflow executions: {error}"
    UPDATE_ERROR = "Error updating workflow execution: {error}"
    DELETE_ERROR = "Error deleting workflow execution: {error}"
    INTERNAL_SERVER_ERROR = "An internal server error occurred"
    VALIDATION_ERROR = "Validation error: {error}"    