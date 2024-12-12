import os
import sys
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import requests  # Using requests to make API calls to the proxy

# Ensure matplotlib does not try to use any X window system
import matplotlib
matplotlib.use('Agg')

# Check if the AI Proxy token is set
if "AIPROXY_TOKEN" not in os.environ:
    print("Error: AIPROXY_TOKEN environment variable not set.")
    sys.exit(1)

# Set OpenAI API key from the environment variable (this will be used for the proxy)
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")

if not AIPROXY_TOKEN:
    print("Error: AIPROXY_TOKEN is not set. Please set the environment variable.")
    sys.exit(1)

# Function to read the CSV file with proper encoding handling
def read_csv_with_encoding(file_path):
    encodings = ['utf-8', 'ISO-8859-1', 'windows-1252', 'utf-16']

    # Try reading the CSV file with different encodings
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            print(f"File successfully read using {encoding} encoding")
            return df
        except UnicodeDecodeError:
            print(f"Failed to read with {encoding} encoding, trying next encoding...")

    # If above attempts fail, use charset-normalizer to detect encoding
    from charset_normalizer import from_path
    try:
        result = from_path(file_path)
        detected_encoding = result.best().encoding
        print(f"Detected encoding: {detected_encoding}")
        df = pd.read_csv(file_path, encoding=detected_encoding)
        return df
    except Exception as e:
        print(f"Error reading file with detected encoding: {e}")
        return None

# Function to interact with the AI Proxy
def analyze_with_llm(summary):
    """Send the dataset summary to the LLM and retrieve insights via the AI Proxy."""
    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"  # AI Proxy URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AIPROXY_TOKEN}"
    }

    data = {
        "model": "gpt-4o-mini",  # Model used in the proxy
        "messages": [
            {"role": "system", "content": "You are an expert data analyst."},
            {"role": "user", "content": f"Analyze this dataset summary: {summary}. Provide key insights."}
        ]
    }

    # Make the request to the AI Proxy
    response = requests.post(url, headers=headers, json=data)

    # Handle response
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print(f"Error communicating with LLM: {response.status_code}, {response.text}")
        return "Could not retrieve insights."

# Function to generate visualizations
def generate_correlation_heatmap(corr_matrix, output_file):
    """Generate a heatmap for the correlation matrix."""
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm")
    plt.title("Correlation Heatmap")
    plt.savefig(output_file)
    plt.close()

def generate_bar_plot(df, column, output_file):
    """Generate a bar plot for a categorical column."""
    plt.figure(figsize=(10, 6))
    df[column].value_counts().plot(kind="bar")
    plt.title(f"Bar Plot for {column}")
    plt.xlabel(column)
    plt.ylabel("Frequency")
    plt.savefig(output_file)
    plt.close()

def generate_readme(summary, insights, image_files):
    """Generate a README.md file summarizing the analysis."""
    with open("README.md", "w") as f:
        f.write("# Automated Data Analysis Report\n\n")
        f.write("## Dataset Summary\n")
        f.write(f"- Shape: {summary['shape']}\n")
        f.write(f"- Columns: {', '.join(summary['columns'])}\n")
        f.write(f"- Missing Values: {summary['missing_values']}\n\n")

        f.write("## Insights from Analysis\n")
        f.write(f"{insights}\n\n")

        f.write("## Visualizations\n")
        for image in image_files:
            f.write(f"![{image}]({image})\n")

# Main function that gets the dataset filename and performs analysis
def main(file_path):
    # Read the file with proper encoding handling
    df = read_csv_with_encoding(file_path)

    # Ensure the DataFrame is not None before proceeding
    if df is not None:
        print("Data successfully loaded.")
        print(f"Data shape: {df.shape}")
        print(f"Column names: {df.columns}")
        print(f"First few rows of the data:\n{df.head()}")  # Example to print the first few rows of the dataset

        # Dataset summary
        summary = {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "sample_data": df.head(5).to_dict(orient="records"),
        }

        print("Dataset summary:", summary)

        # Perform basic analysis
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            correlation_matrix = df[numeric_cols].corr()
        else:
            correlation_matrix = None

        # Generate insights using LLM
        llm_insights = analyze_with_llm(summary)

        # Generate visualizations
        image_files = []
        if numeric_cols:
            generate_correlation_heatmap(correlation_matrix, "correlation_heatmap.png")
            image_files.append("correlation_heatmap.png")

        for col in df.select_dtypes(include=["object", "category"]).columns:
            generate_bar_plot(df, col, f"barplot_{col}.png")
            image_files.append(f"barplot_{col}.png")

        # Generate README.md
        generate_readme(summary, llm_insights, image_files)

    else:
        print("Failed to read the CSV file. Please check the file encoding or format.")

# Run the script with command-line argument
if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]  # Get the filename from the command-line argument
        main(file_path)
    else:
        print("Please provide the file path as an argument.")
        sys.exit(1)

