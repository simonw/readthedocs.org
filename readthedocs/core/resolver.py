"""
Read the Docs URL Resolver.

Url Types:

- Subproject
- Subdomain
- CNAME
- Single Version
- Normal

All possible URL's::

    Subdomain or CNAME:

    /<lang>/<version>/<filename> # Default
    /<filename> # Single Version
    /projects/<subproject_slug>/<lang>/<version>/<filename> # Subproject
    /projects/<subproject_slug>/<filename> # Subproject Single Version

    Normal Serving:

    /docs/<project_slug>/<lang>/<version>/<filename> # Default
    /docs/<project_slug>/<filename> # Single Version
    /docs/<project_slug>/projects/<subproject_slug>/<lang>/<version>/<filename> # Subproject
    /docs/<project_slug>/projects/<subproject_slug>/<filename> # Subproject Single Version
"""

from django.conf import settings


def base_resolve_path(project_slug, filename, version_slug=None, language=None,
                      single_version=None, subproject_slug=None,  subdomain=None, cname=None):
    """ Resolve a with nothing smart, just filling in the blanks."""
    filename = filename.lstrip('/')

    if subdomain or cname:
        url = '/'
    else:
        url = '/docs/{project_slug}/'

    if subproject_slug:
        url += 'projects/{subproject_slug}/'

    if single_version:
        url += '{filename}'
    else:
        url += '{language}/{version_slug}/{filename}'

    return url.format(
        project_slug=project_slug, filename=filename,
        version_slug=version_slug, language=language,
        single_version=single_version, subproject_slug=subproject_slug,
    )


def resolve_path(project, filename='', version_slug=None, language=None,
                 single_version=None, subdomain=None, cname=None):
    """ Resolve a URL with a subset of fields defined."""
    subdomain = getattr(settings, 'USE_SUBDOMAIN', False)
    relation = project.superprojects.first()
    cname = cname or project.domains.filter(canonical=True).first()
    main_language_project = project.main_language_project

    version_slug = version_slug or project.get_default_version()
    language = language or project.language

    if main_language_project:
        project_slug = main_language_project.slug
        language = project.language
        subproject_slug = None
    elif relation:
        project_slug = relation.parent.slug
        subproject_slug = relation.child.slug
    else:
        project_slug = project.slug
        subproject_slug = None

    if project.single_version or single_version:
        single_version = True
    else:
        single_version = False

    return base_resolve_path(project_slug=project_slug, filename=filename,
                             version_slug=version_slug, language=language,
                             single_version=single_version, subproject_slug=subproject_slug,
                             subdomain=subdomain, cname=cname)


def smart_resolve_path(project, filename=''):
    """ Resolve a URL with all fields automatically filled in from the project."""
    subdomain = getattr(settings, 'USE_SUBDOMAIN', False)
    relation = project.superprojects.first()
    cname = project.domains.filter(canonical=True).first()
    main_language_project = project.main_language_project

    version_slug = project.get_default_version()
    language = project.language

    if main_language_project:
        project_slug = main_language_project.slug
        language = project.language
        subproject_slug = None
    elif relation:
        project_slug = relation.parent.slug
        subproject_slug = relation.child.slug
    else:
        project_slug = project.slug
        subproject_slug = None

    if project.single_version:
        single_version = True
    else:
        single_version = False

    return base_resolve_path(project_slug=project_slug, filename=filename,
                             version_slug=version_slug, language=language,
                             single_version=single_version, subproject_slug=subproject_slug,
                             subdomain=subdomain, cname=cname)


def smart_resolve_domain(project):
    main_language_project = project.main_language_project
    relation = project.superprojects.first()
    subdomain = getattr(settings, 'USE_SUBDOMAIN', False)
    prod_domain = getattr(settings, 'PRODUCTION_DOMAIN')
    if main_language_project:
        canonical_project = main_language_project
    elif relation:
        canonical_project = relation.parent
    else:
        canonical_project = project

    domain = canonical_project.domains.filter(canonical=True).first()
    if domain:
        return domain.clean_host
    elif subdomain:
        subdomain_slug = canonical_project.slug.replace('_', '-')
        return "%s.%s" % (subdomain_slug, prod_domain)
    else:
        return prod_domain


def smart_resolve(project, protocol='http', filename=''):
    return '{protocol}://{domain}{path}'.format(
        protocol=protocol,
        domain=smart_resolve_domain(project),
        path=smart_resolve_path(project, filename=filename),
    )


def resolve(project, protocol='http', filename='', **kwargs):
    return '{protocol}://{domain}{path}'.format(
        protocol=protocol,
        domain=smart_resolve_domain(project),
        path=resolve_path(project, filename=filename, **kwargs),
    )
