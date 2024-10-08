from enum import Enum
import os
from pathlib import Path

from pydantic import Field

from tools import Tool

base_folder = "dev"


class WriteOperation(Enum):
    CREATE_FILE = "create-file"
    APPEND_FILE = "append-file"
    OVERWRITE_FILE = "overwrite-file"


class WriteTextFile(Tool):
    """
    Open file for writing and modification.
    """

    directory: str = Field(
        ..., description="Path to the directory where the file is located or will be created. Without filename !!!!"
    )

    filename_without_extension: str = Field(..., description="Name of the target file without the file extension.")

    filename_extension: str = Field(
        ..., description="File extension indicating the file type, such as '.txt', '.py', '.md', etc."
    )

    write_operation: WriteOperation = Field(
        ..., description="Write operation performed, 'create-file', 'append-file' or 'overwrite-file'"
    )

    # Allow free output for the File Content to Enhance LLM Output

    file_content: str = Field(..., description="Triple quoted string for unconstrained output.")

    def run(self, agent):

        if self.directory == "":
            self.directory = "./"
        if self.filename_extension == "":
            self.filename_extension = ".txt"
        if self.filename_extension[0] != ".":
            self.filename_extension = "." + self.filename_extension
        if self.directory[0] == "." and len(self.directory) == 1:
            self.directory = "./"

        if self.directory[0] == "." and len(self.directory) > 1 and self.directory[1] != "/":
            self.directory = "./" + self.directory[1:]

        if self.directory[0] == "/":
            self.directory = self.directory[1:]

        if self.directory.endswith(f"{self.filename_without_extension}{self.filename_extension}"):
            self.directory = self.directory.replace(f"{self.filename_without_extension}{self.filename_extension}", "")
        file_path = os.path.join(self.directory, f"{self.filename_without_extension}{self.filename_extension}")
        file_path = os.path.join(base_folder, file_path)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Determine the write mode based on the write_operation attribute
        if self.write_operation == WriteOperation.CREATE_FILE:
            write_mode = "w"  # Create a new file, error if file exists
        elif self.write_operation == WriteOperation.APPEND_FILE:
            write_mode = "a"  # Append if file exists, create if not
        elif self.write_operation == WriteOperation.OVERWRITE_FILE:
            write_mode = "w"  # Overwrite file if it exists, create if not
        else:
            raise ValueError(f"Invalid write operation: {self.write_operation}")

        # Write back to file
        with open(file_path, write_mode, encoding="utf-8") as file:
            file.writelines(self.file_content)

        return f"Content written to '{self.filename_without_extension}{self.filename_extension}'."


class ReadTextFile(Tool):
    """
    Reads the text content of a specified file and returns it.
    """

    directory: str = Field(description="Path to the directory containing the file. Without filename !!!!")

    file_name: str = Field(
        ..., description="The name of the file to be read, including its extension (e.g., 'document.txt')."
    )

    def run(self, agent):
        try:
            if self.directory.endswith(f"{self.file_name}"):
                self.directory = self.directory.replace(f"{self.file_name}", "")
            if not os.path.exists(f"{base_folder}/{self.directory}/{self.file_name}"):
                return f"File '{self.directory}/{self.file_name}' doesn't exists!"
            with open(f"{base_folder}/{self.directory}/{self.file_name}", "r", encoding="utf-8") as f:
                content = f.read()
            if content.strip() == "":
                return f"File '{self.file_name}' is empty!"
        except Exception as e:
            return f"Error reading file '{self.file_name}': {e}"
        return f"File '{self.file_name}':\n{content}"


class GetFileList(Tool):
    """
    Scans a specified directory and creates a list of all files within that directory, including files in its subdirectories.
    """

    directory: str = Field(
        description="Path to the directory where files will be listed. This path can include subdirectories to be scanned."
    )

    def run(self, agent):
        filenames = "File List:\n"
        counter = 1
        base_path = Path(base_folder) / self.directory

        for root, _, files in os.walk(os.path.join(base_folder, self.directory)):
            for file in files:
                relative_root = Path(root).relative_to(base_path)
                filenames += f"{counter}. {relative_root / file}\n"
                counter += 1

        if counter == 1:
            return f"Directory '{self.directory}' is empty!"
        return filenames
