# -*- coding: utf-8 -*-
import logging

from elasticsearch_dsl import FacetedSearch, TermsFacet
from elasticsearch_dsl.query import Bool, SimpleQueryString

from readthedocs.search.documents import (
    DomainDocument,
    PageDocument,
    ProjectDocument,
)
from readthedocs.search.signals import (
    before_domain_search,
    before_file_search,
    before_project_search,
)

from readthedocs.core.utils.extend import SettingsOverrideObject

log = logging.getLogger(__name__)


ALL_FACETS = ['project', 'version', 'doc_type', 'language', 'index']


class RTDFacetedSearch(FacetedSearch):

    def __init__(self, user, **kwargs):
        self.user = user
        self.filter_by_user = kwargs.pop('filter_by_user', None)
        for facet in self.facets:
            if facet in kwargs:
                kwargs.setdefault('filters', {})[facet] = kwargs.pop(facet)

        # Don't pass along unnecessary filters
        for f in ALL_FACETS:
            if f in kwargs:
                del kwargs[f]
        super(RTDFacetedSearch, self).__init__(**kwargs)

    def search(self):
        """
        Pass in a user in order to filter search results by privacy.

        .. warning::

            The `self.user` attribute isn't currently used on the .org,
            but is used on the .com
        """
        s = super().search()
        s = s.source(exclude=['content', 'headers'])
        resp = self.signal.send(sender=self, user=self.user, search=s)
        if resp:
            # Signal return a search object
            try:
                s = resp[0][1]
            except AttributeError:
                log.exception(
                    'Failed to return a search object from search signals'
                )
        # Return 25 results
        return s[:25]

    def query(self, search, query):
        """
        Add query part to ``search`` when needed.

        Also:

        * Adds SimpleQueryString instead of default query.
        * Adds HTML encoding of results to avoid XSS issues.
        """
        search = search.highlight_options(encoder='html', number_of_fragments=3)

        all_queries = []

        # need to search for both 'and' and 'or' operations
        # the score of and should be higher as it satisfies both or and and
        for operator in ['and', 'or']:
            query_string = SimpleQueryString(
                query=query, fields=self.fields, default_operator=operator
            )
            all_queries.append(query_string)

        # run bool query with should, so it returns result where either of the query matches
        bool_query = Bool(should=all_queries)

        search = search.query(bool_query)
        return search


class DomainSearch(RTDFacetedSearch):
    facets = {
        'project': TermsFacet(field='project'),
        'version': TermsFacet(field='version'),
        'doc_type': TermsFacet(field='doc_type'),
    }
    signal = before_domain_search
    doc_types = [DomainDocument]
    index = DomainDocument._doc_type.index
    fields = ('display_name^5', 'name')


class ProjectSearch(RTDFacetedSearch):
    facets = {
        'language': TermsFacet(field='language')
    }
    signal = before_project_search
    doc_types = [ProjectDocument]
    index = ProjectDocument._doc_type.index
    fields = ('name^10', 'slug^5', 'description')


class PageSearchBase(RTDFacetedSearch):
    facets = {
        'project': TermsFacet(field='project'),
        'version': TermsFacet(field='version')
    }
    doc_types = [PageDocument]
    index = PageDocument._doc_type.index
    fields = ['title^10', 'headers^5', 'content']


class AllSearch(RTDFacetedSearch):
    facets = {
        'project': TermsFacet(field='project'),
        'version': TermsFacet(field='version'),
        'language': TermsFacet(field='language'),
        'doc_type': TermsFacet(field='doc_type'),
        'index': TermsFacet(field='_index'),
    }
    signal = before_file_search
    doc_types = [DomainDocument, PageDocument, ProjectDocument]
    index = [DomainDocument._doc_type.index,
             PageDocument._doc_type.index,
             ProjectDocument._doc_type.index]
    fields = ('title^10', 'headers^5', 'content', 'name^20',
              'slug^5', 'description', 'display_name^5')