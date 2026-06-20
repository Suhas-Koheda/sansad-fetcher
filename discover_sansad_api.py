def main():
    endpoints = [
        {
            "name": "Session Calendar Dates API",
            "url": "https://sansad.in/api_ls/business/AllLoksabhaAndSessionDates",
            "method": "GET",
            "request_payload": "None (No query parameters or request body)",
            "response_schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "loksabha": {"type": "integer", "description": "Lok Sabha term number"},
                        "sessions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "sessionNo": {"type": "integer", "description": "Session number"},
                                    "sessionPeriod": {"type": "array", "items": {"type": "string"}},
                                    "dates": {"type": "array", "items": {"type": "string", "format": "DD/MM/YYYY"}}
                                }
                            }
                        }
                    }
                }
            }
        },
        {
            "name": "Text of Debate / PDF Retrieval API",
            "url": "https://sansad.in/api_ls/debate/text-of-debate?loksabha={loksabha}&sessionNo={sessionNo}&debateDate={debateDate}&locale=en",
            "method": "GET",
            "request_payload": "Query Parameters:\n  - loksabha: integer (e.g. 18)\n  - sessionNo: Roman numeral string (e.g. VII)\n  - debateDate: MM/DD/YYYY formatted date (e.g. 01/28/2026)\n  - locale: string (e.g. en)",
            "response_schema": {
                "type": "object",
                "properties": {
                    "pdfUrl": {"type": "string", "description": "URL to directly fetch the PDF file"}
                }
            }
        },
        {
            "name": "Direct PDF Streaming Handler",
            "url": "https://sansad.in/getFile/dms/fetch/{uuid}?source=dsp2",
            "method": "GET",
            "request_payload": "Path parameter {uuid} and query parameter source=dsp2",
            "response_schema": "Binary stream (Application/PDF)"
        }
    ]
    
    for idx, ep in enumerate(endpoints):
        print(f"\n--- Discovered Endpoint #{idx + 1}: {ep['name']} ---")
        print(f"URL: {ep['url']}")
        print(f"Method: {ep['method']}")
        print(f"Request Payload: {ep['request_payload']}")
        print("Response Schema:")
        import json
        if isinstance(ep['response_schema'], dict):
            print(json.dumps(ep['response_schema'], indent=2))
        else:
            print(f"  {ep['response_schema']}")
        print("-" * 50)

if __name__ == "__main__":
    main()
