

#include <chrono>

#undef TRACEPOINT_PROVIDER
#define TRACEPOINT_PROVIDER tensile_tracing 

#undef TRACEPOINT_INCLUDE
#define TRACEPOINT_INCLUDE "./Tensile/Tensile-tp.hpp"

#if !defined(_TENSILE_TP_H) || defined(TRACEPOINT_HEADER_MULTI_READ)
#define _TENSILE_TP_H

#include <lttng/tracepoint.h>

/*
TRACEPOINT_EVENT(
    tensile_tracing,
    my_first_tracepoint,
    TP_ARGS(
        int, my_integer_arg,
        char*, my_string_arg
    ),
    TP_FIELDS(
        ctf_string(my_string_field, my_string_arg)
        ctf_integer(int, my_integer_field, my_integer_arg)
    )
)*/


TRACEPOINT_EVENT(
    tensile_tracing,
    trace_time,
    TP_ARGS(
        double, trace_duration_arg,
        char*, trace_function_arg
    ),
    TP_FIELDS(
        ctf_string(trace_function, trace_function_arg)
        ctf_float(double, trace_duration, trace_duration_arg)
    )
)




#endif /* _TENSILE_TP_H */

#include <lttng/tracepoint-event.h>
