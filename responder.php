#!/usr/bin/env php
<?php

$status  = (int)($_GET['status'] ?? 200);
$cache   =      $_GET['cache']   ?? '';
$type    =      $_GET['type']    ?? 'text/plain';
$content =      $_GET['content'] ?? 'Hello!';

header('Status: ' . $status);
if ($cache) {
        header('Cache-Control: ' . $cache);
}
header('Content-Type: ' . $type);

echo $content;
