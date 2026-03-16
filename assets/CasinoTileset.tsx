<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" name="CasinoTileset" tilewidth="16" tileheight="16" spacing="0" margin="0" tilecount="2048" columns="64">
 <image source="2D_TopDown_Tileset_Casino_1024x512.png" width="1024" height="512"/>

 <!-- ═══════════════════════════════════════════════════════
      TILES DE COL·LISIÓ — marca els que bloquegen el pas
      Afegeix la propietat: collides = true
      ═══════════════════════════════════════════════════════ -->

 <!-- Parets / objectes sòlids (exemples — ajusta al teu mapa) -->
 <tile id="0">  <properties><property name="collides" type="bool" value="true"/></properties></tile>
 <tile id="1">  <properties><property name="collides" type="bool" value="true"/></properties></tile>
 <tile id="2">  <properties><property name="collides" type="bool" value="true"/></properties></tile>
 <tile id="3">  <properties><property name="collides" type="bool" value="true"/></properties></tile>
 <tile id="64"> <properties><property name="collides" type="bool" value="true"/></properties></tile>
 <tile id="65"> <properties><property name="collides" type="bool" value="true"/></properties></tile>
 <tile id="66"> <properties><property name="collides" type="bool" value="true"/></properties></tile>
 <tile id="67"> <properties><property name="collides" type="bool" value="true"/></properties></tile>

 <!-- ═══════════════════════════════════════════════════════
      ZONES DE JOC — marca amb zone = "poker/blackjack/roulette"
      ═══════════════════════════════════════════════════════ -->
 <!-- Exemples — assigna la propietat als tiles de les taules de joc -->
 <!-- <tile id="XXX"><properties><property name="zone" value="poker"/></properties></tile> -->

</tileset>
