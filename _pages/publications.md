---
layout: archive
title: ""
permalink: /publications/
author_profile: true
---

<!--
  Sections are driven purely by the `type` field that
  `markdown_generator/pubsFromBib.py` writes into each file in `_publications`.
  Do not re-derive the type from venue strings here: the classification lives in
  `markdown_generator/publications_model.py` and can be overridden per work in
  `_data/publication_overrides.yml`.
-->

You can find all of my works on [arXiv](http://arxiv.org/a/muller_j_3).

{% assign sorted_pubs = site.publications | sort: "date" | reverse %}
{% assign preprints = sorted_pubs | where: "type", "preprint" %}
{% assign published = sorted_pubs | where: "type", "published" %}
{% assign workshops = sorted_pubs | where: "type", "workshop" %}

## Preprints

<ol reversed start="{{ preprints | size }}">
{% for pub in preprints %}
  <li>{{ pub.citation }}{% if pub.link %} <a href="{{ pub.link }}" target="_blank">[Access paper]</a>{% endif %}</li>
{% endfor %}
</ol>

## Publications

<ol reversed start="{{ published | size }}">
{% for pub in published %}
  <li>{{ pub.citation }}{% if pub.link %} <a href="{{ pub.link }}" target="_blank">[Access paper]</a>{% endif %}</li>
{% endfor %}
</ol>

## Workshop Papers

<ol reversed start="{{ workshops | size }}">
{% for pub in workshops %}
  <li>{{ pub.citation }}{% if pub.link %} <a href="{{ pub.link }}" target="_blank">[Access paper]</a>{% endif %}</li>
{% endfor %}
</ol>
