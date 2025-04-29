# Forum Application

A client-server forum application with UDP for commands and TCP for file transfers.

## Overview

This application implements a forum system with the following features:
- User authentication
- Thread management (create, list, read, remove)
- Message management (post, edit, delete)
- File transfers (upload, download)

## Architecture

- UDP for command operations
- TCP for file transfers
- Reliable data transfer over UDP using ACK/retransmission

## Components

1. **Server**: `server.py`
2. **Client**: `client.py`
3. **Test Utilities**: `run_test.py`
4. **Sample File**: `testfile.py`
5. **Credentials**: `credentials.txt`

## Getting Started

### Running the Server

```bash
python server.py <port>
```

Example:
```bash
python server.py 9090
```

### Running the Client

```bash
python client.py <port>
```

Example:
```bash
python client.py 9090
```

## Available Commands

Once authenticated, you can use the following commands in the client:

- **CRT**: Create a new thread
  ```
  CRT threadtitle
  ```

- **LST**: List available threads
  ```
  LST
  ```

- **MSG**: Post a message to a thread
  ```
  MSG threadtitle message
  ```

- **DLT**: Delete a message
  ```
  DLT threadtitle messagenumber
  ```

- **RDT**: Read a thread
  ```
  RDT threadtitle
  ```

- **EDT**: Edit a message
  ```
  EDT threadtitle messagenumber newmessage
  ```

- **UPD**: Upload a file to a thread
  ```
  UPD threadtitle filename
  ```

- **DWN**: Download a file from a thread
  ```
  DWN threadtitle filename
  ```

- **RMV**: Remove a thread (creator only)
  ```
  RMV threadtitle
  ```

- **XIT**: Exit the application
  ```
  XIT
  ```

## Testing

Run the automated test script:

```bash
python run_test.py
```

This will test:
- Concurrent client connections
- Thread operations
- Message operations
- File transfers

## File Structure

- `server.py`: Server implementation
- `client.py`: Client implementation
- `run_test.py`: Test utility
- `testfile.py`: Sample file for testing
- `credentials.txt`: User credentials

## Authentication

The application uses a simple username/password authentication system with the credentials stored in the `credentials.txt` file. New users can be created at login time if the username doesn't exist.

## License

This software is provided  for educational purposes.