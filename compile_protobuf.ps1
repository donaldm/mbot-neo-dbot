$scriptPath = split-path -parent $MyInvocation.MyCommand.Definition

$folders = "messages", "dbot-intent-service/messages"

foreach ($folder in $folders)
{
    New-Item -Path $folder -ItemType Directory -Force
    protoc -I=protobufs --python_out=$folder protobufs\DBotCommand.proto
    protoc -I=protobufs --python_out=$folder protobufs\DBotStatus.proto
    protoc -I=protobufs --python_out=$folder protobufs\DBotIntent.proto
}