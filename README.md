# Innovation Week FY25 - Autogen AI Agents using JSON Schema to extract data

#### to create a python virtual environment, run these commands 
```bash
where python or where python3
#then take the path and replace it in the command below
virtualenv -p {python path} venv --prompt="gen_ai_agents"
source venv/bin/activate
python3 -m pip install -r requirements.txt

## Chainlit
[Sample app](https://github.com/Chainlit/cookbook/blob/main/pyautogen/app.py)

## Database Commands

# Demo Project using Autogen Multi-Conversational Agents and Chainlit

### to start Postgres container run this command
```commandline
docker run -d -p 5432:5432 --name iw25-gen-ai -e POSTGRES_PASSWORD=mysecretpassword postgres
```
### then after that if stopped, run this command to start it back up
```commandline
docker start iw25-gen-ai
```

### to stop the Postgres container run this command
```commandline
docker stop iw25-gen-ai
```
### run this command to access the Postgres container
```commandline
docker exec -it iw25-gen-ai bash
```

### to access the Postgres database run this command
### then to create our database run this command
```commandline

su - postgres
psql -c "ALTER USER postgres WITH PASSWORD 'mysecretpassword';"

psql -c 'create database iw25_gen_ai;'
psql
\c iw25_gen_ai
CREATE TABLE transcript_summaries( transcript_id VARCHAR(20), transcript_summary JSONB);
```

### run this command to insert a row into the table
```commandline
INSERT INTO transcript_summaries (transcript_id, transcript_summary) VALUES ('123456', '{"summary":"The customer called Geek Squad to inquire about a specific type of printer they bought. The customer provided the order number 806185814326. The agent redirected the customer to the right department, but the customer expressed frustration as they had already been on hold for 12 minutes and got disconnected. The agent offered a $20 gift card for the trouble, but the customer declined. The call ended with the customer being put on hold.","orderNumber":"806185814326","productSKU":"","driver":"","photos":false,"agentCall":false,"contactType":"Phone","productSafetyFlag":false,"customerNeed":"Technical support","employeeResponse":"Referred to other team - unable to help","customerSentimentGoingIn":{"sentiment":"Neutral","reasoning":"Customer seemed frustrated and in need of assistance"},"customerSentimentGoingOut":{"sentiment":"Neutral","reasoning":"Customer declined the gift card and was put on hold, still frustrated."},"agentName":"Valerie","customerName":"","giftCards":{"giftCardOffered":true,"giftCardAmount":"$20","giftCardAccepted":false}}');
```

### test that the row is inserted
```commandline
psql
\c iw25_gen_ai
select * from transcript_summaries;

```
