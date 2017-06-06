import logging
import datetime
from piecrust.data.filters import PaginationFilter, IFilterClause
from piecrust.dataproviders.pageiterator import (
    PageIterator, HardCodedFilterIterator, DateSortIterator)
from piecrust.page import Page
from piecrust.pipelines._pagebaker import PageBaker
from piecrust.pipelines._pagerecords import PagePipelineRecordEntry
from piecrust.pipelines.base import (
    ContentPipeline, get_record_name_for_source)
from piecrust.routing import RouteParameter
from piecrust.sources.base import ContentItem
from piecrust.sources.generator import GeneratorSourceBase


logger = logging.getLogger(__name__)


_year_index = """---
layout: %(template)s
---
"""


class BlogArchivesSource(GeneratorSourceBase):
    SOURCE_NAME = 'blog_archives'
    DEFAULT_PIPELINE_NAME = 'blog_archives'

    def __init__(self, app, name, config):
        super().__init__(app, name, config)

        tpl_name = config.get('template', '_year.html')
        self._raw_item = _year_index % {'template': tpl_name}

    def getSupportedRouteParameters(self):
        return [RouteParameter('year', RouteParameter.TYPE_INT4)]

    def findContent(self, route_params):
        year = route_params['year']
        spec = '_index[%04d]' % year
        metadata = {'route_params': {'year': year}}
        return ContentItem(spec, metadata)

    def prepareRenderContext(self, ctx):
        ctx.pagination_source = self.inner_source

        route_params = ctx.page.source_metadata['route_params']
        year = route_params.get('year')
        if year is None:
            raise Exception(
                "Can't find the archive year in the route metadata")
        if type(year) is not int:
            raise Exception(
                "The route for generator '%s' should specify an integer "
                "parameter for 'year'." % self.name)

        flt = PaginationFilter()
        flt.addClause(IsFromYearFilterClause(year))
        ctx.pagination_filter = flt

        ctx.custom_data['year'] = year

        flt2 = PaginationFilter()
        flt2.addClause(IsFromYearFilterClause(year))
        it = PageIterator(self.inner_source)
        it._simpleNonSortedWrap(HardCodedFilterIterator, flt2)
        it._wrapAsSort(DateSortIterator, reverse=False)
        ctx.custom_data['archives'] = it

    def _bakeDirtyYears(self, ctx, all_years, dirty_years):
        route = self.app.getGeneratorRoute(self.name)
        if route is None:
            raise Exception(
                "No routes have been defined for generator: %s" %
                self.name)

        logger.debug("Using archive page: %s" % self.page_ref)
        fac = self.page_ref.getFactory()

        for y in dirty_years:
            extra_route_metadata = {'year': y}

            logger.debug("Queuing: %s [%s]" % (fac.ref_spec, y))
            ctx.queueBakeJob(fac, route, extra_route_metadata, str(y))
        ctx.runJobQueue()


class IsFromYearFilterClause(IFilterClause):
    def __init__(self, year):
        self.year = year

    def pageMatches(self, fil, page):
        return (page.datetime.year == self.year)


def _date_sorter(it):
    return sorted(it, key=lambda x: x.datetime)


class BlogArchivesPipelineRecordEntry(PagePipelineRecordEntry):
    def __init__(self):
        super().__init__()
        self.year = None


class BlogArchivesPipeline(ContentPipeline):
    PIPELINE_NAME = 'blog_archives'
    PASS_NUM = 1
    RECORD_ENTRY_CLASS = BlogArchivesPipelineRecordEntry

    def __init__(self, source, ctx):
        if not isinstance(source, BlogArchivesSource):
            raise Exception("The blog archives pipeline only supports blog "
                            "archives content sources.")

        super().__init__(source, ctx)
        self.inner_source = source.inner_source
        self._tpl_name = source.config['template']
        self._all_years = None
        self._dirty_years = None
        self._pagebaker = None

    def initialize(self):
        self._pagebaker = PageBaker(self.app,
                                    self.ctx.out_dir,
                                    force=self.ctx.force)
        self._pagebaker.startWriterQueue()

    def shutdown(self):
        self._pagebaker.stopWriterQueue()

    def createJobs(self, ctx):
        logger.debug("Building blog archives for: %s" %
                     self.inner_source.name)
        self._buildDirtyYears(ctx)
        logger.debug("Got %d dirty years out of %d." %
                     (len(self._dirty_years), len(self._all_years)))

        jobs = []
        for y in self._dirty_years:
            item = ContentItem(
                '_index[%04d]' % y,
                {'route_params': {'year': y}})
            jobs.append(self.createJob(item))
        if len(jobs) > 0:
            return jobs
        return None

    def run(self, job, ctx, result):
        page = Page(self.source, job.content_item)
        prev_entry = ctx.previous_entry
        cur_entry = result.record_entry
        cur_entry.year = job.content_item.metadata['route_params']['year']
        self._pagebaker.bake(page, prev_entry, cur_entry, [])

    def postJobRun(self, ctx):
        # Create bake entries for the years that were *not* dirty.
        # Otherwise, when checking for deleted pages, we would not find any
        # outputs and would delete those files.
        all_str_years = [str(y) for y in self._all_years]
        for prev, cur in ctx.record_history.diffs:
            if prev and not cur:
                y = prev.year
                if y in all_str_years:
                    logger.debug(
                        "Creating unbaked entry for year %s archive." % y)
                    cur.year = y
                    cur.out_paths = list(prev.out_paths)
                    cur.errors = list(prev.errors)
                else:
                    logger.debug(
                        "No page references year %s anymore." % y)

    def _buildDirtyYears(self, ctx):
        all_years = set()
        dirty_years = set()

        record_name = get_record_name_for_source(self.inner_source)
        current_records = ctx.record_histories.current
        cur_rec = current_records.getRecord(record_name)
        for cur_entry in cur_rec.getEntries():
            dt = datetime.datetime.fromtimestamp(cur_entry.timestamp)
            all_years.add(dt.year)
            if cur_entry.was_any_sub_baked:
                dirty_years.add(dt.year)

        self._all_years = all_years
        self._dirty_years = dirty_years

