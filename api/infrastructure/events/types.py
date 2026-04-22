
# api/events/types.py

# Its purpose is to define a canonical, centralized identifier for an event.

# Instead of writing:
#    dispatch("clinical_event_occurred", payload)
# you write:
#    dispatch(EVENT_CLINICAL_EVENT_OCCURRED, payload)


EVENT_CLINICAL_EVENT_OCCURRED = "clinical_event_occurred"