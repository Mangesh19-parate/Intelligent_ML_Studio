import urllib.request
import json
import uuid

# 1. Login with demo account
data = json.dumps({'email': 'trainer@demo.com', 'password': 'DemoPassword123!'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:5000/api/v1/auth/login', data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
token = json.loads(resp.read().decode('utf-8'))['access_token']

print('1. Auth Token successfully acquired.')

# 2. Get or create project
req = urllib.request.Request('http://127.0.0.1:5000/api/v1/projects', headers={'Authorization': f'Bearer {token}'})
projects = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
if projects:
    project = projects[0]
else:
    data = json.dumps({'project_name': 'Customer Churn Live Slice', 'target_column': 'churn'}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:5000/api/v1/projects', data=data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
    project = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))

project_id = project['id']
print(f'2. Active Project: "{project["project_name"]}" (ID: {project_id})')

# 3. Upload dataset using multipart/form-data
boundary = '----WebKitFormBoundary' + uuid.uuid4().hex
with open('backend/sample_customers.csv', 'rb') as f:
    file_bytes = f.read()

part1 = f'--{boundary}\r\nContent-Disposition: form-data; name="project_id"\r\n\r\n{project_id}\r\n'.encode('utf-8')
part2 = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="sample_customers.csv"\r\nContent-Type: text/csv\r\n\r\n'.encode('utf-8')
part3 = f'\r\n--{boundary}--\r\n'.encode('utf-8')

body = part1 + part2 + file_bytes + part3

req = urllib.request.Request(
    'http://127.0.0.1:5000/api/v1/datasets/upload',
    data=body,
    headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Authorization': f'Bearer {token}'
    }
)
try:
    res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    print(f'3. Dataset Uploaded: version {res["version_number"]}, Stage: {res["stage"]}, Hash: {res["content_hash"][:16]}..., Rows: {res["row_count"]}, Cols: {res["column_count"]}')
    dataset_id = res['id']
except urllib.error.HTTPError as e:
    err_msg = e.read().decode('utf-8')
    print(f'3. Upload info: {err_msg}')
    req = urllib.request.Request(f'http://127.0.0.1:5000/api/v1/projects/{project_id}/datasets', headers={'Authorization': f'Bearer {token}'})
    dss = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    dataset_id = dss[0]['id']
    print(f'   Using existing dataset: {dataset_id}')

# 4. Check structural schema
req = urllib.request.Request(f'http://127.0.0.1:5000/api/v1/datasets/{dataset_id}/columns', headers={'Authorization': f'Bearer {token}'})
cols = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
print('4. Structural Schema Inferred:')
for c in cols:
    print(f'   - {c["column_name"]}: dtype={c["data_type"]}, missing={c["missing_percentage"]}%, unique={c["unique_count"]}, target={c.get("is_target", False)}')

# 5. Lock Outer Split
split_body = json.dumps({'locked_test_pct': 20, 'seed': 42}).encode('utf-8')
req = urllib.request.Request(
    f'http://127.0.0.1:5000/api/v1/datasets/{dataset_id}/split',
    data=split_body,
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
)
try:
    split_res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    print(f'5. Outer Split LOCKED: Dev={split_res["development_rows"]} ({100-split_res["locked_test_pct"]}%), Locked Test={split_res["locked_test_rows"]} ({split_res["locked_test_pct"]}%), Seed={split_res["split_seed"]}, Stratified={split_res["is_stratified"]}')
except urllib.error.HTTPError as e:
    req = urllib.request.Request(f'http://127.0.0.1:5000/api/v1/datasets/{dataset_id}/split', headers={'Authorization': f'Bearer {token}'})
    split_res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    print(f'5. Existing Split: Dev={split_res["development_rows"]} ({100-split_res["locked_test_pct"]}%), Locked Test={split_res["locked_test_rows"]} ({split_res["locked_test_pct"]}%), Seed={split_res["split_seed"]}, Stratified={split_res["is_stratified"]}')

# 6. Fetch Development Preview
req = urllib.request.Request(f'http://127.0.0.1:5000/api/v1/datasets/{dataset_id}/development-preview?limit=10', headers={'Authorization': f'Bearer {token}'})
prev = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
print(f'6. Development Partition Preview: Received {len(prev["preview_rows"])} sample rows out of {prev["total_development_rows"]} total development rows.')
print('   First row preview:', prev['preview_rows'][0])
