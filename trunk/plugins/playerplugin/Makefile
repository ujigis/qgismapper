
UIC=pyuic4
RCC=pyrcc4
UI_SOURCES=$(wildcard *.ui SourcePlugins/*.ui)
UI_FILES=$(patsubst %.ui,%_ui.py,$(UI_SOURCES))

all: resources_rc.py ${UI_FILES}

resources_rc.py: resources.qrc
	${RCC} -o resources_rc.py resources.qrc

$(UI_FILES): %_ui.py: %.ui
	${UIC} $< > $@

clean:
	find . -name '*.pyc' -exec rm '{}' ';'
	find . -name '*~' -exec rm '{}' ';'
	rm -f ${UI_FILES}
