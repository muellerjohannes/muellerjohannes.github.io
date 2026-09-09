---
layout: archive
title: ""
permalink: /publications/
author_profile: true
---

You can find all of my works on [arXiv](http://arxiv.org/a/muller_j_3).

{% assign sorted_pubs = site.publications | sort: "date" | reverse %}
{% assign seen_titles = "|" %}

## Publications

<ol>
{% for pub in sorted_pubs %}
  {% assign venue_norm = pub.venue | default: "" | downcase %}
  {% assign type_norm = pub.type | default: "" | downcase %}
  {% assign is_main_conf = false %}
  {% if venue_norm contains "international conference on machine learning" or venue_norm contains " icml" or venue_norm == "icml" or venue_norm contains "advances in neural information processing systems" or venue_norm contains "neurips" or venue_norm contains "conference on neural information processing systems" or venue_norm contains "international conference on learning representations" or venue_norm contains " iclr" or venue_norm == "iclr" %}
    {% assign is_main_conf = true %}
  {% endif %}
  {% assign is_workshop = false %}
  {% if venue_norm contains "workshop" or venue_norm contains "symposium" or venue_norm contains "satellite" %}
    {% assign is_workshop = true %}
  {% endif %}
  {% assign is_preprint_like = false %}
  {% if venue_norm contains "arxiv preprint" or type_norm == "preprint" or type_norm == "arxiv" %}
    {% assign is_preprint_like = true %}
  {% endif %}
  {% assign is_arxiv_venue = false %}
  {% if venue_norm contains "arxiv preprint" %}
    {% assign is_arxiv_venue = true %}
  {% endif %}

  {% assign show_here = false %}
  {% if is_main_conf %}
    {% assign show_here = true %}
  {% elsif is_workshop == false and type_norm == "published" %}
    {% assign show_here = true %}
  {% elsif is_workshop == false and is_preprint_like and is_arxiv_venue == false %}
    {% assign show_here = true %}
  {% endif %}

  {% assign norm_title = pub.title | default: "" | downcase | strip %}
  {% capture marker %}|{{ norm_title }}|{% endcapture %}
  {% if show_here %}
  {% unless seen_titles contains marker %}
    <li>{{ pub.citation }}{% if pub.link %} <a href="{{ pub.link }}" target="_blank">[Access paper]</a>{% endif %}</li>
    {% capture seen_titles %}{{ seen_titles }}{{ marker }}{% endcapture %}
  {% endunless %}
  {% endif %}
{% endfor %}
</ol>

## Workshop Papers

<ol>
{% for pub in sorted_pubs %}
  {% assign venue_norm = pub.venue | default: "" | downcase %}
  {% assign is_main_conf = false %}
  {% if venue_norm contains "international conference on machine learning" or venue_norm contains " icml" or venue_norm == "icml" or venue_norm contains "advances in neural information processing systems" or venue_norm contains "neurips" or venue_norm contains "conference on neural information processing systems" or venue_norm contains "international conference on learning representations" or venue_norm contains " iclr" or venue_norm == "iclr" %}
    {% assign is_main_conf = true %}
  {% endif %}
  {% assign is_workshop = false %}
  {% if venue_norm contains "workshop" or venue_norm contains "symposium" or venue_norm contains "satellite" %}
    {% assign is_workshop = true %}
  {% endif %}

  {% assign norm_title = pub.title | default: "" | downcase | strip %}
  {% capture marker %}|{{ norm_title }}|{% endcapture %}
  {% if is_workshop and is_main_conf == false %}
  {% unless seen_titles contains marker %}
    <li>{{ pub.citation }}{% if pub.link %} <a href="{{ pub.link }}" target="_blank">[Access paper]</a>{% endif %}</li>
    {% capture seen_titles %}{{ seen_titles }}{{ marker }}{% endcapture %}
  {% endunless %}
  {% endif %}
{% endfor %}
</ol>

## Preprints

<ol>
{% for pub in sorted_pubs %}
  {% assign venue_norm = pub.venue | default: "" | downcase %}
  {% assign type_norm = pub.type | default: "" | downcase %}
  {% assign is_main_conf = false %}
  {% if venue_norm contains "international conference on machine learning" or venue_norm contains " icml" or venue_norm == "icml" or venue_norm contains "advances in neural information processing systems" or venue_norm contains "neurips" or venue_norm contains "conference on neural information processing systems" or venue_norm contains "international conference on learning representations" or venue_norm contains " iclr" or venue_norm == "iclr" %}
    {% assign is_main_conf = true %}
  {% endif %}
  {% assign is_workshop = false %}
  {% if venue_norm contains "workshop" or venue_norm contains "symposium" or venue_norm contains "satellite" %}
    {% assign is_workshop = true %}
  {% endif %}
  {% assign is_preprint_like = false %}
  {% if venue_norm contains "arxiv preprint" or type_norm == "preprint" or type_norm == "arxiv" %}
    {% assign is_preprint_like = true %}
  {% endif %}

  {% assign norm_title = pub.title | default: "" | downcase | strip %}
  {% capture marker %}|{{ norm_title }}|{% endcapture %}
  {% if is_preprint_like and is_main_conf == false and is_workshop == false %}
  {% unless seen_titles contains marker %}
    <li>{{ pub.citation }}{% if pub.link %} <a href="{{ pub.link }}" target="_blank">[Access paper]</a>{% endif %}</li>
    {% capture seen_titles %}{{ seen_titles }}{{ marker }}{% endcapture %}
  {% endunless %}
  {% endif %}
{% endfor %}
</ol>
