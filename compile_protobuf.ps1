$scriptPath = split-path -parent $MyInvocation.MyCommand.Definition

$folders = "messages", "dbot-intent-service/messages"
$protobufs = "DBotCommand.proto", "DBotStatus.proto", "DBotIntent.proto"

foreach ($folder in $folders)
{
    New-Item -Path $folder -ItemType Directory -Force
    foreach ($protobuf in $protobufs)
    {
        $protobufPath = Join-Path -Path 'protobufs' -ChildPath $protobuf
        protoc -I=protobufs --python_out =$folder protobufs\$protobufPath
    }
}