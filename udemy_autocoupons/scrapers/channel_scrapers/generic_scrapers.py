"""A module that contains all the generic scrapers for the channels."""
from udemy_autocoupons.scrapers.channel_scrapers.channel_scraper import (
    ChannelScraper,
)
from udemy_autocoupons.scrapers.channel_scrapers.generic_process_message import (
    generic_process_message,
)

bestudemydeals_scraper = ChannelScraper(
    channel_id="bestudemydeals",
    process_message=generic_process_message,
)
leveryth_scraper = ChannelScraper(
    channel_id="leveryth",
    process_message=generic_process_message,
)
idownloadcoupon_scraper = ChannelScraper(
    channel_id="idownloadcoupon",
    process_message=generic_process_message,
)
mcp_scraper = ChannelScraper(
    channel_id="MastercursosProgramacion",
    process_message=generic_process_message,
)
udemycodes_scraper = ChannelScraper(
    channel_id="Udemycodes",
    process_message=generic_process_message,
)
uce_scraper = ChannelScraper(
    channel_id="UdemyCuponesEsp",
    process_message=generic_process_message,
)
edn_scraper = ChannelScraper(
    channel_id="everydaynewcourses",
    process_message=generic_process_message,
)
udemycoures_scraper = ChannelScraper(
    channel_id="udemy_coures",
    process_message=generic_process_message,
)
udemyfreebies_scraper = ChannelScraper(
    channel_id="subudemyfreebies",
    process_message=generic_process_message,
)
ufcwc_scraper = ChannelScraper(
    channel_id="udemy_free_courses_with_certi",
    process_message=generic_process_message,
)

generic_scrapers: tuple[ChannelScraper, ...] = (
    bestudemydeals_scraper,
    leveryth_scraper,
    idownloadcoupon_scraper,
    mcp_scraper,
    udemycodes_scraper,
    uce_scraper,
    edn_scraper,
    udemycoures_scraper,
    udemyfreebies_scraper,
    ufcwc_scraper,
)
