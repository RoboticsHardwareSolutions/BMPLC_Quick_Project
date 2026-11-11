#pragma once

/* Classic double-fork daemonization. Must be called before any threads are created or
 * file descriptors (serial port, sockets) are opened -- fork() in a multi-threaded
 * process only carries the calling thread into the child, so this has to happen first.
 *
 * On success, the calling process has become a detached background child (both parent
 * processes along the way have already _exit()'d) and this returns 0. stdin/stdout/
 * stderr are redirected to /dev/null, or to `log_file_path` for stdout+stderr if given.
 * Never returns in the two parents. */
int tb_daemonize(const char* log_file_path);

/* Writes the current process's pid to `pidfile_path`. Returns 0 on success. */
int  tb_write_pidfile(const char* pidfile_path);
void tb_remove_pidfile(const char* pidfile_path);
