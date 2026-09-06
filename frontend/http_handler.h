#pragma once

static inline void http_fn(struct mg_connection* c, int ev, void* ev_data)
{
    if (ev == MG_EV_HTTP_MSG)
    {
        struct mg_http_message* hm = (struct mg_http_message*) ev_data;
        if (mg_match(hm->uri, mg_str("/api/info"), NULL))
        {
            if (!mg_strcmp(hm->method, mg_str("GET")))
            {
                mg_http_reply(c,
                              200,
                              "Content-Type: application/json\r\n",
                              "{%m:%m}",
                              MG_ESC("bmplc_type"),
#if defined(BMPLC_M)
                              MG_ESC("BMPLC_M")
#elif defined(BMPLC_XL)
                              MG_ESC("BMPLC_XL")
#else
                              MG_ESC("Custom")
#endif
                );
            }
        }
        else if (mg_match(hm->uri, mg_str("/api/tasks"), NULL))
        {
            if (!mg_strcmp(hm->method, mg_str("GET")))
            {
                static RHSThreadList* thread_list = NULL;
                if (!thread_list)
                    thread_list = rhs_thread_list_create();

                uint16_t count;

                rhs_thread_enumerate(thread_list);  // 0.9 ms
                count = rhs_thread_list_size(thread_list);

                char   body[1024];
                size_t off = 0;

                for (size_t i = 0; i < count; i++)  // 0.3 ms
                {
                    RHSThreadListItem* item = rhs_thread_list_at(thread_list, i);

                    if (sizeof(body) - off < 64)
                        break;

                    off += mg_snprintf(body + off,
                                       sizeof(body) - off,
                                       "%s{%m:%m, %m:%u, %m:%f, %m:%u}",
                                       (i > 0) ? "," : "",
                                       MG_ESC("task"),
                                       MG_ESC(item->name),
                                       MG_ESC("priority"),
                                       item->priority,
                                       MG_ESC("load"),
                                       item->cpu,
                                       MG_ESC("stack_min_free"),
                                       item->stack_min_free);
                }

                // rhs_thread_list_destroy(thread_list);
                mg_http_reply(c,
                              200,
                              "Content-Type: application/json\r\n",
                              "{%m:[%s]}",
                              MG_ESC("tasks"),
                              body);  // 0.1 ms
            }
        }  // 1.3 ms
        else
        {
            struct mg_http_serve_opts opts = {0};
            opts.root_dir                  = "/dist";
            opts.fs                        = &mg_fs_packed;
            mg_mem_files                   = mg_packed_files;

            mg_http_serve_dir(c, ev_data, &opts);
        }
    }
}
