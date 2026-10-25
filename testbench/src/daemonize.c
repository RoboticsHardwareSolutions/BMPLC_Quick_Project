#include "daemonize.h"

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

int tb_daemonize(const char* log_file_path)
{
    pid_t pid = fork();
    if (pid < 0)
        return -1;
    if (pid > 0)
        _exit(0); /* first parent: done, hand off to the shell immediately */

    if (setsid() < 0) /* detach from the controlling terminal, become session leader */
        return -1;

    /* Second fork so the daemon can never re-acquire a controlling terminal (it's no
     * longer a session leader itself). */
    pid = fork();
    if (pid < 0)
        return -1;
    if (pid > 0)
        _exit(0);

    umask(0);
    if (chdir("/") != 0)
    {
        /* non-fatal: just means we might hold whatever directory we started in busy */
    }

    int devnull = open("/dev/null", O_RDWR);
    if (devnull >= 0)
    {
        dup2(devnull, STDIN_FILENO);
        if (!log_file_path || log_file_path[0] == '\0')
        {
            dup2(devnull, STDOUT_FILENO);
            dup2(devnull, STDERR_FILENO);
        }
        if (devnull > STDERR_FILENO)
            close(devnull);
    }

    if (log_file_path && log_file_path[0] != '\0')
    {
        int logfd = open(log_file_path, O_WRONLY | O_CREAT | O_APPEND, 0644);
        if (logfd >= 0)
        {
            dup2(logfd, STDOUT_FILENO);
            dup2(logfd, STDERR_FILENO);
            if (logfd > STDERR_FILENO)
                close(logfd);
        }
    }

    return 0;
}

int tb_write_pidfile(const char* pidfile_path)
{
    FILE* f = fopen(pidfile_path, "w");
    if (!f)
        return -1;
    fprintf(f, "%d\n", (int) getpid());
    fclose(f);
    return 0;
}

void tb_remove_pidfile(const char* pidfile_path)
{
    unlink(pidfile_path);
}
