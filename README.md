# Docker clipboard dispatcher

Uses docker volume to share data between container and host. 

All you need is to clone this repo and execute `clipdis_setup.py` script:

```sh
git clone https://github.com/edKotinsky/clipdis.git
python3 clipdis_setup.py -i (host|container) [-e]
```

`-i` option is required, it specifies the type of installation. When module
installed on host, it provides the `clipdis_start` command, which starts
your docker container and watches the specified clipboard directory.
When module installed in container, it provides a bunch of commands: `c`, `p`,
`xclip`, `pb-paste`, etc., which are actually the wrappers for the module.

`-e` option installs module in develop mode.

Currently it will not work on Windows.

## How it works

There are two parts: clipboard tool and watcher. 

Tool is a container's part.
It mimics the real clipboard tools as xsel, xclip, wl-copy, etc. It just reads
and writes data from the file, that is placed into the volume directory,
into the standard input/output.

Watcher is a part that is run on a host's side. When it starts, it acts as
a wrapper for a container TTY, and asyncronously watches files in the directory,
where the container's clipboard volume is mounted. It performs writing and
reading of the data from these files into host's clipboard.

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
integrated with the container itself, just manually tested on a host.

## License

Licensed under MIT License.
