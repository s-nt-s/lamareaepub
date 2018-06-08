#!/bin/bash

IDS=$(calibredb search title:"La Marea #")
if [ ! -z "$IDS" ]; then
	calibredb remove $IDS
fi

cd out/epub
calibredb add *.epub
IDS=$(calibredb search title:"La Marea #")

while IFS=',' read -ra ADDR; do
	for i in "${ADDR[@]}"; do
		calibredb set_custom myshelves "$i" "La Marea"
	done
done <<< "$IDS"
