# Docker clipboard dispatcher

Uses docker volume to share data between container and host. 

All you need is to copy module directory to the container and add its `bin`
directory to container's PATH environment variable. On the host you need to add
the following alias:

```sh
alias start-doc="python3 -m cb 
```

Will not work on Windows.

## How it works

There are two parts: clipboard tool and watcher. 

Tool is a container's part.
It mimics the real clipboard tools as xsel, xclip, wl-copy, etc. It just reads
and writes data from the file, that is placed into the volume directory,
into the standard input/output. It requires the name of a tool to determine an
operation to perform: copy or paste.

Watcher is a part that is run on a host's side. When it starts, it creates an 
orphaned process, that monitors files in the container's volume directory,
and reads/writes data between the host's clipboard and files in the directory.
It requires container ID to check, if the container is alive. If not, then
the process exits. 

There are two files: `.state` for storing the state and `.data` to store the
data respectively. Possible states are: PASTE, when the container's tool
requests data from host's clipboard; COPY, when the container's tool
sends data from stdin to host's clipboard; DONE, when the watcher puts data
into `.data` file; and NONE, which means "no operation". State is required to
manage access to `.data` file, to avoid race and data overwriting.

### Copy from Container to Host

![Copy operation diagram](./resources/copy.png "Copy diagram")

### Paste from Host to Container

![Paste operation diagram](./resources/paste.png "Paste diagram")

## Disclaimer

I wrote this thing not long ago, so it is quite raw and buggy. It is still not
integrated with the container itself, just tested on a host.

## License

Licensed under MIT License.
