# Prompt for AI Coding Assistant

## Project Overview
I want to create a unified command-line tool in Python that enhances the workflow of using AI coding assistants like the Gemini CLI or Codex. This tool will streamline three main tasks: capturing the session of the CLI tool, analyzing the session to generate insights and improve configuration files, and summarizing the session for documentation purposes.

## Key Features

1. **Configuration:**
   The tool should accept a configuration file or command-line parameters specifying:
   - The AI model to use (e.g., Gemini, Codex).
   - The CLI tool to be instrumented (e.g., Gemini CLI).
   - The path to the global configuration file of the CLI tool.

2. **Session Capture:**
   The tool will launch the specified CLI tool and record the entire session. It will offer two options for capturing the session:
   - Using the `script` command (for systems where `script` is available).
   - A Python-based alternative (preferred for better portability if it works well).

3. **Analysis and Improvement:**
   The tool can operate in two modes:
   - **Default Mode:** Runs the CLI tool, captures the session, and automatically analyzes the session log to identify pain points and suggest improvements to the configuration.
   - **Analysis Mode:** The user can provide an existing session log file. The tool will then analyze the session and/or generate a summary without needing to re-run the CLI tool.

4. **Session Summary:**
   The tool will generate a concise summary of the session, detailing the actions taken, commands executed, and any changes made. This summary can be used for documentation or future reference.

## Usage

The tool can be run in two ways:
- **Default Mode:** With a configuration file or command-line parameters, it launches the CLI tool and processes the session.
- **Analysis Mode:** By providing an existing session log file, the tool will analyze the session and generate a summary without re-running the CLI tool.

## Goal

This tool aims to improve the efficiency and usability of AI coding assistants by providing continuous feedback and making the configuration more adaptive over time.
