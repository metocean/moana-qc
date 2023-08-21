for file in ;do
    curl -X PUT --data-binary file http://kt-mhs01:11120/mhs/queue;
done