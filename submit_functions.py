from docx import Document
import odf.text
from odf.opendocument import load
import os
import subprocess
import tempfile
import textract

def read_file_content(file_path):
    """Helper function to read different file formats"""
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.txt':
        with open(file_path, 'r') as file:
            return file.read()
    
    elif file_extension == '.docx':
        doc = Document(file_path)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    
    elif file_extension == '.doc':
        try:
            return textract.process(file_path).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to read .doc file: {str(e)}")
    
    elif file_extension == '.odt':
        doc = load(file_path)
        text_elements = doc.getElementsByType(odf.text.P)
        return '\n'.join([element.firstChild.data for element in text_elements if element.firstChild])
    
    elif file_extension == '.pages':        
        with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
            try:
                subprocess.run(['textutil', '-convert', 'txt', '-output', temp_file.name, file_path], check=True, capture_output=True)
                with open(temp_file.name, 'r') as f:
                    return f.read()
            except subprocess.CalledProcessError:
                raise ValueError("Failed to convert .pages file. Please ensure the file is not corrupted.")
    
    elif file_extension == '.pdf':
        try:
            return textract.process(file_path).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to read .pdf file: {str(e)}")
    
    elif file_extension == '.pptx':
        try:
            return textract.process(file_path).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to read .pptx file: {str(e)}")

    elif file_extension == '.rtf':
        try:
            return textract.process(file_path).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to read .rtf file: {str(e)}")

    else:
        raise ValueError(f"Unsupported file format: {file_extension}")
