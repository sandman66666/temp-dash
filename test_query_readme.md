# OpenSearch Query Tests

These test queries will help us determine if the `.keyword` suffix is causing issues with our trace_id queries.

## Setup

1. Set your OpenSearch credentials as environment variables:
```bash
export OPENSEARCH_USERNAME=elkadmin
export OPENSEARCH_PASSWORD=your_password
```

2. Run the test script:
```bash
./test_query.sh
```

## What the Tests Do

1. **Test 1**: Simple query without `.keyword`
   - Tests if we can find any events using trace_id without .keyword
   - This will help determine if the field is indexed without the .keyword suffix

2. **Test 2**: Simple query with `.keyword`
   - Tests if we can find any events using trace_id.keyword
   - This will help determine if the field is indexed with the .keyword suffix

3. **Test 3**: Check index mapping
   - Shows the actual field mappings in the index
   - Will reveal how the trace_id field is actually indexed

4. **Test 4**: Full query without `.keyword`
   - Tests the complete power users query without .keyword suffixes
   - Includes event filtering and aggregations

5. **Test 5**: Full query with `.keyword`
   - Tests the complete power users query with .keyword suffixes
   - This is what we're currently using in the code

6. **Test 6**: Check event names
   - Lists all available event_names in the index
   - Helps verify we're using the correct event name for message threads

## Expected Results

- If we get results from Test 1 but not Test 2, we should remove .keyword
- If we get results from Test 2 but not Test 1, we should keep .keyword
- Test 3 will show us definitively how the fields are mapped
- Test 6 will confirm the exact event name we should be using

## Troubleshooting

If you get authentication errors:
- Verify your environment variables are set correctly
- Check that the OpenSearch credentials are correct

If you get no results:
- Check the mapping from Test 3 to see how fields are actually named
- Look at the event names from Test 6 to verify the correct event name
- Try a single user ID that you know exists in the system