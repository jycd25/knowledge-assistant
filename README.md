# Knowledge Assistant

A powerful knowledge management system that helps you organize, search, and interact with your documents.

## Features

- **PDF Processing**: Convert PDF documents to markdown format
- **Knowledge Base Management**: Organize documents into categories and topics
- **Vector Search**: Find information using semantic search powered by OpenAI embeddings
- **Note Taking**: Create and manage notes
- **Template Generation**: Create templates for various document types

## Setup

### Prerequisites

- Python 3.9+
- OpenAI API key (for embeddings and AI features)

### Quick Start

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your OpenAI API key in the .env file:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   ```
4. Run the application using the runner script:
   ```bash
   python run.py
   ```

### Using the Python Runner Script

The `run.py` script provides an easy way to manage the Knowledge Assistant:

```bash
# Run the file
python run.py

# Initialize the database before running
python run.py --init-db


# Use a specific port
python run.py --port 8080

# Reset the database (WARNING: deletes all data)
python run.py --reset-db

# Check dependencies only, don't run the app
python run.py --check

# Enable file watching (for development)
python run.py --enable-watch
```

### Alternative Setup Methods

If you prefer, you can also use:

1. The setup script for a complete setup and launch:
   ```bash
   ./setup.sh
   ```

2. Manual database initialization:
   ```bash
   python utils/init_db.py
   ```

3. Manual application start:
   ```bash
   streamlit run app/app_st.py --server.fileWatcherType none
   ```

## Usage

Once the application is running, access it in your browser at:
- Local URL: http://localhost:8501/
- Network URL: Shown in the terminal output

### Getting Started

1. **Add Documents**: Use the PDF Converter tab to upload and process PDF documents
   - Upload a PDF
   - Process it
   - Add it to the knowledge base

2. **Organize Knowledge**: In the KB Manager tab, you can:
   - Create categories for broad subject areas
   - Add topics within those categories
   - Organize your documents in this hierarchy

3. **Search Your Knowledge**: Use the KB Search tab to find information across your knowledge base using:
   - Keyword search
   - Semantic (meaning-based) search powered by OpenAI embeddings

4. **Create Notes**: Use the Note Processor to create and manage notes, with optional integration into your knowledge base

## Troubleshooting

### Common Issues

- **Missing Tables Error**: If you see errors about missing tables, run the initialization script:
  ```bash
  python run.py --init-db
  ```

- **Full-Text Search Issues**: Install the tantivy package for improved search:
  ```bash
  pip install tantivy
  ```

- **OpenAI API Errors**: Ensure your API key is correctly set in the .env file

- **Database Reset**: If you need to start fresh, you can reset the database:
  ```bash
  python run.py --reset-db
  ```
  Warning: This will delete all data in your knowledge base.

## Project Structure

- `app/`: Streamlit interface components
- `tools/`: Core functionality modules
- `utils/`: Helper utilities
- `data/`: Storage for knowledge base and uploads
- `run.py`: Main runner script for the application
- `setup.sh`: Setup script for first-time installation

## License

This project is licensed under the MIT License - see the LICENSE file for details. 